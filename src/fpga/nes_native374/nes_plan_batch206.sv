// SPDX-License-Identifier: MIT
// Wire E9 remains compressed. Host admission constructs fixed32B records in
// the existing1KiB dual-clock RAM. No NES operand/shortform/alt-list decoder.
module nes_plan_batch206 #(parameter SHARED_CRC307=0)(
 output wire [9:0] plan_cursor319,output wire plan_zero319,plan_step319,
 input wire host_clk,nes_clk,reset,active,stop,source_fault,
 input wire write_valid,output wire write_ready,input wire [7:0] write_data,
 input wire retire,output reg retire_done,
 input wire retire_permitted,output wire retire_commit,
 input wire seal,input wire [9:0] seal_length,input wire [4:0] seal_plans,input wire [15:0] seal_crc,
 output wire host_idle,output wire fault,
 input wire lease_valid,input wire [15:0] lease_generation,
 output wire plan_valid,input wire plan_ready,tile_done,
 output reg [1:0] plan_kind,output reg [15:0] plan_generation,
 output reg [9:0] plan_slot,output reg [12:0] plan_tag,
 output reg [47:0] plan_rows,output reg [7:0] plan_mask,plan_alt_mask,
 output wire [103:0] plan_alt_tags,
 output wire end_valid,output wire end_partial295,input wire end_ready,output wire [15:0] end_generation
);
 wire raw=reset||!active||stop||source_fault;
 wire hr,nr;nes_domain_reset124 hrelease(.clk(host_clk),.raw_reset(raw),.reset(hr));
 nes_domain_reset124 nrelease(.clk(nes_clk),.raw_reset(raw),.reset(nr));
 reg hf,nf;wire cancel=raw||hf||nf;assign fault=hf||nf||source_fault;
 wire hc,nc;
 nes_domain_reset124 hcancel(.clk(host_clk),.raw_reset(cancel),.reset(hc));
 nes_domain_reset124 ncancel(.clk(nes_clk),.raw_reset(cancel),.reset(nc));
 // Single physical M9K, including byte write enables; same vendor model in simulation.
 reg [9:0] count;reg [15:0] crc;
 reg pending,writer,reader,retire_pending,retire_wait;reg [4:0] plans,remaining;
 wire box_ready,word_valid,word_ready;wire [5:0] word;
 reg [4:0] records374;reg [5:0] wire_at374,wire_length374;
 reg short374,clear374;reg [2:0] clear_word374;reg [7:0] kind374,alt_left374;
 nes_native_mailbox206 #(.WIDTH(6)) control(.src_clk(host_clk),.dst_clk(nes_clk),.reset(cancel),
  .src_valid(pending&&!hc),.src_ready(box_ready),.src_data({writer,plans}),
  .dst_valid(word_valid),.dst_ready(word_ready),.dst_data(word));
 wire retire_ready,retire_valid;wire retire_word;
 wire retire_ack=!nc&&retire_valid&&retire_permitted;
 nes_native_mailbox206 #(.WIDTH(1)) rearm(.src_clk(host_clk),.dst_clk(nes_clk),.reset(cancel),
  .src_valid(retire_pending&&!hc),.src_ready(retire_ready),.src_data(1'b1),
  .dst_valid(retire_valid),.dst_ready(retire_ack),.dst_data(retire_word));
 assign write_ready=!hr&&!hc&&!pending&&!retire_pending&&!retire_wait&&!clear374&&count<512&&records374<16;
 assign host_idle=!hr&&!hc&&!pending&&!retire_pending&&!retire_wait&&!clear374&&count==0;
 function automatic [15:0] crc16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer i;begin c=c0^{b,8'd0};for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction
 function automatic [3:0] popcount(input [7:0] b);
  integer i;begin popcount=0;for(i=0;i<8;i=i+1)popcount=popcount+b[i];end
 endfunction
 function automatic [2:0] first_bit374(input [7:0] b);
  integer i;begin first_bit374=0;for(i=7;i>=0;i=i-1)if(b[i])first_bit374=3'(i);end
 endfunction
 reg [4:0] native_byte374;
 always @*begin
  native_byte374=0;
  if(short374)native_byte374=wire_at374[4:0];
  else case(wire_at374)
   0:native_byte374=0;1:native_byte374=14;
   2,3,4,5,6,7,8,9,10,11,12,13,14:native_byte374=wire_at374[4:0]-5'd1;
   15:native_byte374=15;
   default:native_byte374=5'd16+{first_bit374(alt_left374),1'b0}+{4'd0,wire_at374[0]};
  endcase
 end
 wire [7:0] native_word_addr374={writer,records374[3:0],native_byte374[4:2]};
 reg [31:0] initial_word374;
 always @*begin
  initial_word374=0;
  case(clear_word374)
   0:initial_word374={24'd0,kind374};
   1:initial_word374=short374&&!kind374[1]?32'hff000000:0;
   2:initial_word374=short374&&!kind374[1]?32'h646d2240:0;
   3:initial_word374=short374&&!kind374[1]?32'h0100ff6b:32'h01000000;
   default:;
  endcase
 end
 // Native words use byte write enables; clear/default writes own the A port
 // for eight host clocks before the next wire byte. An over-fast sender faults.
 wire byte_write374=write_valid&&write_ready&&wire_at374!=0;
 wire [7:0] write_word374=clear374?{writer,records374[3:0],clear_word374}:native_word_addr374;
 wire [31:0] write_value374=clear374?initial_word374:{4{write_data}};
 wire [3:0] write_mask374=clear374?4'b1111:byte_write374?(4'b1<<native_byte374[1:0]):4'b0;
 reg [2:0] fetch_word374;reg [3:0] record374;wire [31:0] data374;
 nes_plan_ram374 payload(.host_clk(host_clk),.nes_clk(nes_clk),
  .write_address(write_word374),.write_data(write_value374),.write_mask((!hr&&!hc)?write_mask374:4'd0),
  .read_address({reader,record374,fetch_word374}),.read_data(data374));
 always @(posedge host_clk or posedge hr)begin
  if(hr)begin
   hf<=0;count<=0;crc<=16'hffff;pending<=0;writer<=0;plans<=0;retire_pending<=0;retire_wait<=0;retire_done<=0;
   records374<=0;wire_at374<=0;wire_length374<=0;short374<=0;kind374<=0;alt_left374<=0;clear374<=0;clear_word374<=0;
  end else if(!hc)begin
   retire_done<=0;
   if(retire)begin
    if(retire_pending||retire_wait||pending||count!=0||clear374)hf<=1;
    else retire_pending<=1;
   end
   if(retire_pending&&retire_ready)begin retire_pending<=0;retire_wait<=1;end
   if(retire_wait&&retire_ready)begin retire_wait<=0;retire_done<=1;end
   if(clear374)begin
    if(clear_word374==7)clear374<=0;else clear_word374<=clear_word374+1'b1;
   end
   if(write_valid)begin
    if(!write_ready)hf<=1;
    else begin
     count<=count+1'b1;if(!SHARED_CRC307)crc<=crc16(crc,write_data);
     if(wire_at374==0)begin
      short374<=write_data[7];kind374<=write_data==8'h87 ? 8'h83:{6'd0,write_data[1:0]};
      if(write_data[7]?(write_data[6:2]!=0&&write_data!=8'h87):write_data[7:2]!=0)hf<=1;
      wire_length374<=write_data[7]?(write_data[1]?6'd3:write_data[0]?6'd8:6'd7):6'd16;
      wire_at374<=1;clear374<=1;clear_word374<=0;alt_left374<=0;
     end else begin
      if(!short374&&wire_at374==1)begin wire_length374<=16+{popcount(write_data),1'b0};alt_left374<=write_data;end
      if(!short374&&wire_at374>=16&&wire_at374[0])begin
       if(write_data[7:5]!=0||alt_left374==0)hf<=1;
       alt_left374<=alt_left374&(alt_left374-1'b1);
      end
      if(!short374&&wire_at374==15&&write_data!=1)hf<=1;
      if(wire_at374==wire_length374-1)begin wire_at374<=0;records374<=records374+1'b1;end
      else wire_at374<=wire_at374+1'b1;
     end
    end
   end
   if(seal)begin
    if(pending||write_valid||clear374||wire_at374!=0||count<3||count>512||seal_length!=count||
      (!SHARED_CRC307&&seal_crc!=crc)||seal_plans==0||seal_plans>16||records374!=seal_plans)hf<=1;
    else begin pending<=1;plans<=seal_plans;end
   end
   if(pending&&box_ready)begin pending<=0;writer<=!writer;count<=0;crc<=16'hffff;records374<=0;end
  end
 end
 localparam WAIT=0,READ=1,CAPTURE=2,CHECK=3,READY=4,RUN=5,ENDING=6;
 reg [2:0] state,capture_word374;
 reg bad,closed,bg_closed295,partial295;reg [12:0] alt[0:7];
 genvar g;generate for(g=0;g<8;g=g+1)begin:alt_out
  assign plan_alt_tags[g*13+:13]=alt[g];
 end endgenerate
 wire shape_ok=!bad&&remaining!=0&&remaining<=16&&(plan_kind!=3||remaining==1)&&
  ((plan_kind==0&&plan_slot!=0&&plan_mask==255)||
   (plan_kind==1&&plan_slot<128&&plan_mask!=0&&plan_alt_mask==0)||
   (plan_kind>=2&&plan_slot==0&&plan_tag==0&&plan_rows==0&&plan_mask==0&&plan_alt_mask==0));
 wire lease_ok=lease_valid&&plan_generation==lease_generation;
 assign word_ready=!nr&&!nc&&state==CHECK&&shape_ok&&lease_ok&&remaining==1;
 assign plan_valid=!nr&&!nc&&state==READY&&lease_ok;
 assign end_valid=!nr&&!nc&&state==ENDING&&lease_ok;
 assign end_generation=plan_generation;assign end_partial295=partial295;
 assign retire_commit=!nr&&retire_ack&&retire_word&&closed&&state==WAIT&&!word_valid&&lease_ok;
 assign plan_cursor319={1'b0,record374,fetch_word374,2'd0};
 assign plan_zero319=!nr&&!nc&&state==WAIT&&word_valid;
 assign plan_step319=!nr&&!nc&&state==CAPTURE&&capture_word374!=7;

 always @(posedge nes_clk or posedge nr)begin
  if(nr)begin nf<=0;state<=WAIT;fetch_word374<=0;capture_word374<=0;record374<=0;bad<=0;reader<=0;remaining<=0;closed<=0;bg_closed295<=0;partial295<=0;end
  else if(!nc)begin
   if(retire_ack)begin
    if(!retire_word||!closed||state!=WAIT||word_valid||!lease_ok)nf<=1;
    else begin closed<=0;bg_closed295<=0;end
   end
   if((state==READY||state==RUN||state==ENDING)&&!lease_ok)nf<=1;
   case(state)
    WAIT:if(word_valid)begin
     if(closed||retire_valid)nf<=1;
     record374<=0;fetch_word374<=0;capture_word374<=0;bad<=0;
     reader<=word[5];remaining<=word[4:0];state<=READ;
    end
    READ:begin fetch_word374<=1;state<=CAPTURE;end
    CAPTURE:begin
     case(capture_word374)
      0:begin plan_kind<=data374[1:0];partial295<=data374[7];plan_generation<=data374[23:8];plan_slot[7:0]<=data374[31:24];if(data374[6:2]!=0)bad<=1;end
      1:begin plan_slot[9:8]<=data374[1:0];plan_tag<=data374[20:8];plan_mask<=data374[31:24];if(data374[7:2]!=0||data374[23:21]!=0)bad<=1;end
      2:plan_rows[31:0]<=data374;
      3:begin plan_rows[47:32]<=data374[15:0];plan_alt_mask<=data374[23:16];if(data374[31:24]!=1)bad<=1;end
      4,5,6,7:begin
       alt[{capture_word374[1:0],1'b0}]<=data374[12:0];alt[{capture_word374[1:0],1'b1}]<=data374[28:16];
       if(data374[15:13]!=0||data374[31:29]!=0)bad<=1;
      end
     endcase
     if(capture_word374==7)state<=CHECK;
     else begin capture_word374<=capture_word374+1'b1;if(fetch_word374!=7)fetch_word374<=fetch_word374+1'b1;end
    end
    CHECK:if(!shape_ok||!lease_ok||(bg_closed295&&(partial295||plan_kind==0||plan_kind==2)))nf<=1;else state<=plan_kind==3?ENDING:READY;
    READY:if(plan_valid&&plan_ready)state<=RUN;
    RUN:if(tile_done)begin
     if(remaining==1)state<=WAIT;
     else begin remaining<=remaining-1'b1;record374<=record374+1'b1;fetch_word374<=0;capture_word374<=0;bad<=0;state<=READ;end
    end
    ENDING:if(end_valid&&end_ready)begin state<=WAIT;if(partial295)bg_closed295<=1;else closed<=1;end
   endcase
  end
 end
endmodule

// Explicit primitive prevents byte-lane FF fallback or four-fragment packing.
// Both functional and board builds use this module and the Intel primitive.
module nes_plan_ram374(input wire host_clk,nes_clk,input wire [7:0] write_address,read_address,
 input wire [31:0] write_data,input wire [3:0] write_mask,output wire [31:0] read_data);
 altsyncram #(.operation_mode("DUAL_PORT"),.intended_device_family("Cyclone IV E"),.ram_block_type("M9K"),
  .width_a(32),.widthad_a(8),.numwords_a(256),.width_b(32),.widthad_b(8),.numwords_b(256),
  .width_byteena_a(4),.byte_size(8),.address_reg_b("CLOCK1"),.outdata_reg_b("UNREGISTERED"),
  .read_during_write_mode_mixed_ports("DONT_CARE"),.power_up_uninitialized("TRUE")) ram(
  .clock0(host_clk),.clock1(nes_clk),.clocken0(1'b1),.clocken1(1'b1),.clocken2(1'b1),.clocken3(1'b1),
  .aclr0(1'b0),.aclr1(1'b0),.address_a(write_address),.data_a(write_data),.wren_a(|write_mask),.byteena_a(write_mask),
  .address_b(read_address),.data_b(32'd0),.wren_b(1'b0),.byteena_b(1'b1),.rden_a(1'b1),.rden_b(1'b1),.addressstall_a(1'b0),.addressstall_b(1'b0),.q_a(),.eccstatus(),.q_b(read_data));
endmodule
