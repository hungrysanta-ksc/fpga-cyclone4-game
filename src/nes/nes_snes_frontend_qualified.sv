// SPDX-License-Identifier: MIT
// 043 bundled bus qualification. See docs/nes-h1-qualified-contract.md.
module nes_snes_frontend(
 input wire host_clk,reset,
 input wire [23:0] snes_addr,
 input wire read_n,write_n,romsel_n,
 input wire [7:0] snes_data_in,
 output wire [7:0] bus_data,
 output wire databus_oe_n,databus_dir,
 output reg reg_write,reg_read,data_read,
 output reg [3:0] reg_address,
 output reg [7:0] reg_wdata,
 input wire [7:0] reg_rdata,data,
 input wire reg_rvalid,data_valid,ready,busy,fault,
 output reg [127:0] frontend_snapshot,
 output reg [3:0] frontend_error
);
 (* async_reg="true" *) reg [1:0] rd_sync,wr_sync,sel_sync;
 reg [23:0] addr_meta,addr_sync,addr_previous,write_address,read_address;
 reg [7:0] data_meta,data_sync,data_previous,write_data,response;
 reg rd_previous,wr_previous,sel_previous,write_conflict,write_seen,read_seen,read_issued;
 reg response_sample_meta,response_sample;
 reg output_valid,payload_pending,local_pending;
 reg [1:0] pending;
 reg [11:0] position;
 reg [7:0] event_cause;
 reg [127:0] event_snapshot;
 function automatic is_reg(input [23:0] a);
  is_reg=a[23:4]==20'h00600 && a[3:0]<=10;
 endfunction
 function automatic is_payload(input [23:0] a);
  is_payload=a>=24'h408000 && a<24'h408c00;
 endfunction
 function automatic [3:0] error_mask(input [7:0] c);
  error_mask={c[6],c[4],c[5],(|c[3:0])};
 endfunction
 // Raw pins are used only for sampling and immediate external bus release.
 wire raw_read=!reset&&!read_n&&write_n;
 wire selected_read=read_address==snes_addr &&
  (is_reg(read_address)||(is_payload(read_address)&&!romsel_n));
 wire drive=raw_read&&selected_read&&output_valid&&
  (is_reg(read_address)||(frontend_error==0 && event_cause==0));
 wire receive_write=!reset&&read_n&&!write_n&&is_reg(snes_addr);
 assign bus_data=response;
 assign databus_dir=drive;
 assign databus_oe_n=!(drive||receive_write);
 // A bundled sample is accepted only after two active samples agree.
 // This tolerates up to one host-clock sample of relative control/address skew;
 // it is not a general asynchronous multibit synchronizer.
 wire active_pair=!rd_sync[1]&&!rd_previous;
 wire stable_bundle=addr_sync==addr_previous && sel_sync[1]==sel_previous;
 wire qualified_read=active_pair && wr_sync[1] && wr_previous && stable_bundle;
 wire start_read=qualified_read&&!read_seen;
 wire tracked_read=read_seen&&(pending!=0||output_valid);
 wire [7:0] causes={1'b0,
  (pending==2 && !local_pending && !(payload_pending ? data_valid : reg_rvalid)),
  (start_read && is_payload(addr_sync) && !sel_sync[1] &&
   !(frontend_error==0 && event_cause==0 && ready && addr_sync[11:0]==position)),
  (active_pair && !wr_sync[1] && !wr_previous),
  (tracked_read && active_pair && stable_bundle && is_payload(read_address) && sel_sync[1]),
  (tracked_read && !wr_sync[1] && !wr_previous),
  (read_issued && rd_sync[1] && !response_sample),
  (tracked_read && qualified_read && addr_sync!=read_address)};
 // Both sticky errors and the FIRST record consume this same registered event.
 // DB stores its mapped error bits, DC..DE the preceding qualified address.
 always @(posedge host_clk or posedge reset) begin
  if(reset)begin event_cause<=0;event_snapshot<=0;frontend_error<=0;frontend_snapshot<=0;end
  else begin
   event_cause<=causes;
   event_snapshot<={8'h43,addr_previous,3'b0,response_sample,error_mask(causes),
    4'b0,position,read_address,addr_sync,
    ready,busy,fault,reg_rvalid,data_valid,sel_sync[1],rd_sync[1],wr_sync[1],
    output_valid,payload_pending,local_pending,read_issued,read_seen,rd_previous,pending,causes};
   frontend_error<=frontend_error|error_mask(event_cause);
   if(frontend_snapshot[7:0]==0 && event_cause!=0)frontend_snapshot<=event_snapshot;
  end
 end
 always @(posedge host_clk or posedge reset) begin
  if(reset) begin
   rd_sync<=3;wr_sync<=3;sel_sync<=3;rd_previous<=1;wr_previous<=1;sel_previous<=1;
   addr_meta<=0;addr_sync<=0;addr_previous<=0;data_meta<=0;data_sync<=0;data_previous<=0;
   response_sample_meta<=0;response_sample<=0;
   write_address<=0;write_data<=0;write_conflict<=0;write_seen<=0;read_seen<=0;read_issued<=0;
   read_address<=0;response<=0;output_valid<=0;pending<=0;
   payload_pending<=0;local_pending<=0;position<=0;
   reg_write<=0;reg_read<=0;data_read<=0;reg_address<=0;reg_wdata<=0;
  end else begin
   rd_sync<={rd_sync[0],read_n};wr_sync<={wr_sync[0],write_n};sel_sync<={sel_sync[0],romsel_n};
   rd_previous<=rd_sync[1];wr_previous<=wr_sync[1];sel_previous<=sel_sync[1];
   addr_meta<=snes_addr;addr_sync<=addr_meta;addr_previous<=addr_sync;
   data_meta<=snes_data_in;data_sync<=data_meta;data_previous<=data_sync;
   // Sample response eligibility at the same edge as the first RD stage.
   // Delayed RD release must not conceal a release before response creation.
   response_sample_meta<=output_valid;response_sample<=response_sample_meta;
   reg_write<=0;reg_read<=0;data_read<=0;
   if(rd_sync[1])begin output_valid<=0;read_seen<=0;read_issued<=0;end
   if(!wr_sync[1])begin
    if(!rd_sync[1])write_conflict<=1;
    if(!wr_previous && rd_sync[1] && rd_previous && addr_sync==addr_previous && data_sync==data_previous)begin
     write_seen<=1;write_address<=addr_sync;write_data<=data_sync;
    end
   end
   // Complete an accepted write after a stable release, exactly once.
   if(wr_sync[1] && wr_previous)begin
    if(write_seen && !write_conflict && is_reg(write_address))begin
     if(write_address[3:0]<=9 && frontend_error==0 && event_cause==0)begin
      reg_write<=1;reg_address<=write_address[3:0];reg_wdata<=write_data;
      if(write_address[3:0]==0 && write_data==1 && !ready && !busy && !fault)position<=0;
     end
    end
    write_seen<=0;write_conflict<=0;
   end
   if(start_read)begin
    read_seen<=is_reg(addr_sync)||(is_payload(addr_sync)&&!sel_sync[1]);
    read_address<=addr_sync;output_valid<=0;read_issued<=0;
    if(is_reg(addr_sync))begin
     read_issued<=1;
     reg_address<=addr_sync[3:0];payload_pending<=0;
     local_pending<=addr_sync[3:0]==10;pending<=1;
     if(addr_sync[3:0]!=10)reg_read<=1;
    end else if(is_payload(addr_sync) && !sel_sync[1])begin
     if(frontend_error==0 && event_cause==0 && ready && addr_sync[11:0]==position)begin
      read_issued<=1;data_read<=1;payload_pending<=1;local_pending<=0;pending<=1;
     end
    end
   end
   if(pending==1)pending<=2;
   if(pending==2)begin
    pending<=0;
    if(local_pending)begin response<={4'b0,frontend_error};output_valid<=1;end
    else if(payload_pending ? data_valid : reg_rvalid)begin
     response<=payload_pending ? data : reg_rdata;output_valid<=1;
     if(payload_pending)position<=position+1'b1;
    end
   end
  end
 end
endmodule
