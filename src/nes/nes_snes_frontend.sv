// SPDX-License-Identifier: MIT
// Original experimental SNES pin frontend for029. See031 contract for pulse bounds.
// Bundled address/data samples are NOT a general multibit synchronizer.
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
 output reg [3:0] frontend_error
);
 (* async_reg="true" *) reg [1:0] rd_sync,wr_sync;
 reg [23:0] addr_meta,addr_sync,write_address,read_address;
 reg [7:0] data_meta,data_sync,write_data,response;
 reg rd_previous,wr_previous,write_conflict,write_seen;
 reg output_valid,payload_pending,local_pending;
 reg [1:0] pending;
 reg [11:0] position;
 function automatic is_reg(input [23:0] a);
  is_reg=a[23:4]==20'h00600 && a[3:0]<=10;
 endfunction
 function automatic is_payload(input [23:0] a);
  is_payload=a>=24'h408000 && a<24'h408c00;
 endfunction
 wire raw_read=!reset&&!read_n&&write_n;
 wire selected_read=read_address==snes_addr &&
  (is_reg(read_address)||(is_payload(read_address)&&!romsel_n));
 wire drive=raw_read&&selected_read&&output_valid&&
  (is_reg(read_address)||frontend_error==0);
 wire receive_write=!reset&&read_n&&!write_n&&is_reg(snes_addr);
 assign bus_data=response;
 assign databus_dir=drive;
 assign databus_oe_n=!(drive||receive_write);
 always @(posedge host_clk or posedge reset) begin
  if(reset) begin
   rd_sync<=3;wr_sync<=3;rd_previous<=1;wr_previous<=1;
   addr_meta<=0;addr_sync<=0;data_meta<=0;data_sync<=0;
   write_address<=0;write_data<=0;write_conflict<=0;write_seen<=0;
   read_address<=0;response<=0;output_valid<=0;pending<=0;
   payload_pending<=0;local_pending<=0;position<=0;
   reg_write<=0;reg_read<=0;data_read<=0;reg_address<=0;reg_wdata<=0;frontend_error<=0;
  end else begin
   rd_sync<={rd_sync[0],read_n};wr_sync<={wr_sync[0],write_n};
   rd_previous<=rd_sync[1];wr_previous<=wr_sync[1];
   addr_meta<=snes_addr;addr_sync<=addr_meta;data_meta<=snes_data_in;data_sync<=data_meta;
   reg_write<=0;reg_read<=0;data_read<=0;
   if(!read_n&&!write_n)frontend_error[2]<=1;
   if(rd_sync[1])output_valid<=0;
   if(!wr_sync[1]) begin
    write_seen<=1;write_address<=addr_sync;write_data<=data_sync;
    if(!rd_sync[1])write_conflict<=1;
   end
   if(wr_sync[1]&&!wr_previous) begin
    if(write_seen && !write_conflict && is_reg(write_address)) begin
     if(write_address[3:0]<=9 && frontend_error==0) begin
      reg_write<=1;reg_address<=write_address[3:0];reg_wdata<=write_data;
      if(write_address[3:0]==0 && write_data==1 && !ready && !busy && !fault)position<=0;
     end
    end
    write_seen<=0;write_conflict<=0;
   end
   if(!rd_sync[1] && rd_previous && raw_read) begin
    read_address<=addr_sync;output_valid<=0;
    if(is_reg(addr_sync)) begin
     reg_address<=addr_sync[3:0];payload_pending<=0;
     local_pending<=addr_sync[3:0]==10;pending<=1;
     if(addr_sync[3:0]!=10)reg_read<=1;
    end else if(is_payload(addr_sync) && !romsel_n) begin
     if(frontend_error==0 && ready && addr_sync[11:0]==position) begin
      data_read<=1;payload_pending<=1;local_pending<=0;pending<=1;
     end else frontend_error[1]<=1;
    end
   end
   if(pending==1)pending<=2;
   if(pending==2) begin
    pending<=0;
    if(local_pending)begin response<={4'b0,frontend_error};output_valid<=1;end
    else if(payload_pending ? data_valid : reg_rvalid)begin
     response<=payload_pending ? data : reg_rdata;output_valid<=1;
     if(payload_pending)position<=position+1'b1;
    end else frontend_error[3]<=1;
   end
   // Address change or premature release invalidates the physical read immediately
   // through combinational OE; latched flags require common reset recovery.
   if((pending!=0 || output_valid) && (!read_n && snes_addr!=read_address))
    frontend_error[0]<=1;
   if(pending!=0 && (read_n || !write_n))frontend_error[0]<=1;
   if((pending!=0 || output_valid) && is_payload(read_address) && romsel_n)
    frontend_error[0]<=1;
  end
 end
endmodule
