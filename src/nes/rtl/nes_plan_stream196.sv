// SPDX-License-Identifier: MIT
// Host byte plan -> immutable32B dual-clock RAM -> NES owned decoded plan.
// Host framing/SPI and geometry epoch capture are external, not synthesized
// here. CRC and exact length must seal before any NES byte becomes visible.
// Pair with source_tile192 EXTERNAL_PLAN=1: decoded fields stay held THROUGH
// tile_done. This replaces its internal field copy, not a second frame buffer.
module nes_plan_stream196(
 input wire host_clk,nes_clk,reset,active,stop,source_fault,
 input wire write_valid,output wire write_ready,input wire [7:0] write_data,
 input wire seal,input wire [5:0] seal_length,input wire [15:0] seal_crc,
 output wire host_idle,output wire fault,
 input wire lease_valid,input wire [15:0] lease_generation,
 output wire plan_valid,input wire plan_ready,tile_done,
 output reg [1:0] plan_kind,output reg [15:0] plan_generation,
 output reg [9:0] plan_slot,output reg [12:0] plan_tag,
 output reg [47:0] plan_rows,output reg [7:0] plan_mask,plan_alt_mask,
 output wire [103:0] plan_alt_tags,
 output wire end_valid,input wire end_ready,output wire [15:0] end_generation
);
 wire raw=reset||!active||stop||source_fault;
 wire hr,nr;nes_domain_reset124 hrelease(.clk(host_clk),.raw_reset(raw),.reset(hr));
 nes_domain_reset124 nrelease(.clk(nes_clk),.raw_reset(raw),.reset(nr));
 reg hf,nf;wire cancel=raw||hf||nf;assign fault=hf||nf||source_fault;
 (* ramstyle="M9K, no_rw_check" *) reg [7:0] payload[0:31];
 reg [7:0] data;reg [5:0] count,at,length;reg [15:0] crc;
 reg [1:0] host_state;wire box_ready,word_valid,word_ready;wire [5:0] word_length;
 nes_native_mailbox165 #(.WIDTH(6)) control(.src_clk(host_clk),.dst_clk(nes_clk),.reset(cancel),
  .src_valid(host_state==1&&!cancel),.src_ready(box_ready),.src_data(count),
  .dst_valid(word_valid),.dst_ready(word_ready),.dst_data(word_length));
 assign write_ready=!hr&&!cancel&&host_state==0&&count<32;
 assign host_idle=write_ready&&count==0&&box_ready;
 function automatic [15:0] crc16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer i;begin c=c0^{b,8'd0};for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction
 always @(posedge host_clk)if(write_valid&&write_ready)payload[count[4:0]]<=write_data;
 always @(posedge host_clk or posedge hr)begin
  if(hr)begin hf<=0;count<=0;crc<=16'hffff;host_state<=0;end
  else if(!cancel)begin
   if(write_valid&&write_ready)begin count<=count+1'b1;crc<=crc16(crc,write_data);end
   if(seal)begin
    if(host_state!=0||write_valid||count<16||count>32||count[0]||seal_length!=count||seal_crc!=crc)hf<=1;
    else host_state<=1;
   end
   if(host_state==1&&box_ready)host_state<=2;
   if(host_state==2&&box_ready)begin host_state<=0;count<=0;crc<=16'hffff;end
  end
 end
 localparam WAIT=0,READ=1,CAPTURE=2,CHECK=3,READY=4,RUN=5,ENDING=6;
 reg [2:0] state;reg bad;reg [3:0] alt_index;reg [12:0] alt[0:7];
 genvar g;generate for(g=0;g<8;g=g+1)begin:alt_out
  assign plan_alt_tags[g*13+:13]=alt[g];
 end endgenerate
 function automatic [3:0] popcount(input [7:0] b);
  integer i;begin popcount=0;for(i=0;i<8;i=i+1)popcount=popcount+b[i];end
 endfunction
 wire shape_ok=!bad&&length==16+{popcount(plan_alt_mask),1'b0}&&
  ((plan_kind==0&&plan_slot!=0&&plan_mask==255)||
   (plan_kind==1&&plan_slot<128&&plan_mask!=0&&plan_alt_mask==0)||
   (plan_kind>=2&&plan_slot==0&&plan_tag==0&&plan_rows==0&&plan_mask==0&&plan_alt_mask==0));
 wire lease_ok=lease_valid&&plan_generation==lease_generation;
 assign word_ready=!nr&&!cancel&&state==CHECK&&shape_ok&&lease_ok;
 assign plan_valid=!nr&&!cancel&&state==READY&&lease_ok;
 assign end_valid=!nr&&!cancel&&state==ENDING&&lease_ok;
 assign end_generation=plan_generation;
 always @(posedge nes_clk)data<=payload[at[4:0]];
 integer i;
 always @(posedge nes_clk or posedge nr)begin
  if(nr)begin nf<=0;state<=WAIT;at<=0;length<=0;bad<=0;alt_index<=0;end
  else if(!cancel)begin
   if((state==READY||state==RUN||state==ENDING)&&!lease_ok)nf<=1;
   case(state)
    WAIT:if(word_valid)begin
     at<=0;length<=word_length;bad<=0;alt_index<=0;
     for(i=0;i<8;i=i+1)alt[i]<=0;
     state<=READ;
    end
    READ:begin
     if(at>=16&&alt_index>=8)nf<=1;
     else if(at>=16&&!plan_alt_mask[alt_index])alt_index<=alt_index+1'b1;
     else state<=CAPTURE;
    end
    CAPTURE:begin
     case(at)
      0:begin plan_kind<=data[1:0];if(data[7:2]!=0)bad<=1;end
      1:plan_alt_mask<=data;
      2:plan_generation[7:0]<=data;3:plan_generation[15:8]<=data;
      4:plan_slot[7:0]<=data;
      5:begin plan_slot[9:8]<=data[1:0];if(data[7:2]!=0)bad<=1;end
      6:plan_tag[7:0]<=data;
      7:begin plan_tag[12:8]<=data[4:0];if(data[7:5]!=0)bad<=1;end
      8:plan_mask<=data;
      9:plan_rows[7:0]<=data;10:plan_rows[15:8]<=data;11:plan_rows[23:16]<=data;
      12:plan_rows[31:24]<=data;13:plan_rows[39:32]<=data;14:plan_rows[47:40]<=data;
      15:if(data!=1)bad<=1;
      default:if(!at[0])alt[alt_index][7:0]<=data;
              else begin alt[alt_index][12:8]<=data[4:0];if(data[7:5]!=0)bad<=1;alt_index<=alt_index+1'b1;end
     endcase
     if(at==length-1)state<=CHECK;else begin at<=at+1'b1;state<=READ;end
    end
    CHECK:if(!shape_ok||!lease_ok)nf<=1;else state<=plan_kind==3?ENDING:READY;
    READY:if(plan_valid&&plan_ready)state<=RUN;
    RUN:if(tile_done)state<=WAIT;
    ENDING:if(end_valid&&end_ready)state<=WAIT;
   endcase
  end
 end
endmodule
