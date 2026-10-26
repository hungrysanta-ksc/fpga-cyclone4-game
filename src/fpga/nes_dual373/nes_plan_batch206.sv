// SPDX-License-Identifier: MIT
// Host byte plan -> two immutable512B banks in one dual-clock RAM -> NES owned decoded plan.
// Batch CRC seals all bytes; mixed short200/full196 plans, no per-plan CRC.
// Host framing/SPI and geometry epoch capture are external, not synthesized
// here. CRC and exact length must seal before any NES byte becomes visible.
// Pair with source_tile192 EXTERNAL_PLAN=1: decoded fields stay held THROUGH
// tile_done. This replaces its internal field copy, not a second frame buffer.
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
 // Internal faults remain latched under the base resets hr/nr. Cancellation
 // gates use separate local releases, so they cannot erase their own cause.
 wire hc,nc;
 nes_domain_reset124 hcancel(.clk(host_clk),.raw_reset(cancel),.reset(hc));
 nes_domain_reset124 ncancel(.clk(nes_clk),.raw_reset(cancel),.reset(nc));
 (* ramstyle="M9K, no_rw_check" *) reg [7:0] payload[0:1023];
 reg [7:0] data;reg [9:0] count,batch_length;reg [9:0] read_cursor314;assign plan_cursor319=read_cursor314;
 always @(posedge nes_clk)if(nr||nc)read_cursor314<=0;else if(plan_zero319)read_cursor314<=0;else if(plan_step319)read_cursor314<=read_cursor314+1'b1;reg [5:0] at,length;reg [15:0] crc;
 reg pending,writer,reader,retire_pending,retire_wait;reg [4:0] plans,remaining;wire box_ready,word_valid,word_ready;wire [15:0] word;
 nes_native_mailbox206 #(.WIDTH(16)) control(.src_clk(host_clk),.dst_clk(nes_clk),.reset(cancel),
  .src_valid(pending&&!hc),.src_ready(box_ready),.src_data({writer,count,plans}),
  .dst_valid(word_valid),.dst_ready(word_ready),.dst_data(word));
 wire retire_ready,retire_valid;wire retire_word;
 wire retire_ack=!nc&&retire_valid&&retire_permitted;
 nes_native_mailbox206 #(.WIDTH(1)) rearm(.src_clk(host_clk),.dst_clk(nes_clk),.reset(cancel),
  .src_valid(retire_pending&&!hc),.src_ready(retire_ready),.src_data(1'b1),
  .dst_valid(retire_valid),.dst_ready(retire_ack),.dst_data(retire_word));
 // Handing a sealed bank to the mailbox makes the OTHER bank writable.
 // Its prior ownership has necessarily returned before the next handoff.
 assign write_ready=!hr&&!hc&&!pending&&!retire_pending&&!retire_wait&&count<512;
 assign host_idle=write_ready&&count==0;
 function automatic [15:0] crc16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer i;begin c=c0^{b,8'd0};for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction
 always @(posedge host_clk)if(write_valid&&write_ready)payload[{writer,count[8:0]}]<=write_data;
 always @(posedge host_clk or posedge hr)begin
  if(hr)begin hf<=0;count<=0;crc<=16'hffff;pending<=0;writer<=0;plans<=0;retire_pending<=0;retire_wait<=0;retire_done<=0;end
  else if(!hc)begin
   retire_done<=0;
   if(retire)begin
    if(retire_pending||retire_wait||pending||count!=0)hf<=1;
    else retire_pending<=1;
   end
   if(retire_pending&&retire_ready)begin retire_pending<=0;retire_wait<=1;end
   if(retire_wait&&retire_ready)begin retire_wait<=0;retire_done<=1;end
   if(write_valid&&write_ready)begin count<=count+1'b1;if(!SHARED_CRC307)crc<=crc16(crc,write_data);end
   if(seal)begin
    if(pending||write_valid||count<3||count>512||seal_length!=count||(!SHARED_CRC307&&seal_crc!=crc)||seal_plans==0||seal_plans>16)hf<=1;
    else begin pending<=1;plans<=seal_plans;end
   end
   if(pending&&box_ready)begin pending<=0;writer<=!writer;count<=0;crc<=16'hffff;end
  end
 end
 localparam WAIT=0,READ=1,CAPTURE=2,CHECK=3,READY=4,RUN=5,ENDING=6;
 reg [2:0] state;reg bad,shortform,closed,bg_closed295,partial295;reg [3:0] alt_index;reg [12:0] alt[0:7];
 genvar g;generate for(g=0;g<8;g=g+1)begin:alt_out
  assign plan_alt_tags[g*13+:13]=alt[g];
 end endgenerate
 function automatic [3:0] popcount(input [7:0] b);
  integer i;begin popcount=0;for(i=0;i<8;i=i+1)popcount=popcount+b[i];end
 endfunction
 wire shape_ok=!bad&&length==(shortform?(plan_kind[1]?6'd3:plan_kind[0]?6'd8:6'd7):6'd16+{popcount(plan_alt_mask),1'b0})&&
  read_cursor314+10'd1<=batch_length&&remaining!=0&&
  (remaining==1 ? read_cursor314+10'd1==batch_length : read_cursor314+10'd1<batch_length)&&
  (plan_kind!=3||remaining==1)&&
  ((plan_kind==0&&plan_slot!=0&&plan_mask==255)||
   (plan_kind==1&&plan_slot<128&&plan_mask!=0&&plan_alt_mask==0)||
   (plan_kind>=2&&plan_slot==0&&plan_tag==0&&plan_rows==0&&plan_mask==0&&plan_alt_mask==0));
 wire lease_ok=lease_valid&&plan_generation==lease_generation;
 assign word_ready=!nr&&!nc&&state==CHECK&&shape_ok&&lease_ok&&remaining==1;
 assign plan_valid=!nr&&!nc&&state==READY&&lease_ok;
 assign end_valid=!nr&&!nc&&state==ENDING&&lease_ok;
 assign end_generation=plan_generation;assign end_partial295=partial295;
 // Same mailbox roundtrip: release the source on the accepted NES edge.
 assign retire_commit=!nr&&retire_ack&&retire_word&&closed&&state==WAIT&&!word_valid&&lease_ok;
 always @(posedge nes_clk)data<=payload[{reader,9'(read_cursor314)}];
 assign plan_zero319=!nr&&!nc&&state==WAIT&&word_valid;
 assign plan_step319=!nr&&!nc&&((state==CAPTURE&&at!=length-1)||(state==RUN&&tile_done&&remaining!=1));
 integer i;
 always @(posedge nes_clk or posedge nr)begin
  if(nr)begin nf<=0;state<=WAIT;at<=0;length<=0;bad<=0;alt_index<=0;reader<=0;batch_length<=0;remaining<=0;shortform<=0;closed<=0;bg_closed295<=0;partial295<=0;end
  else if(!nc)begin
   if(retire_ack)begin
    if(!retire_word||!closed||state!=WAIT||word_valid||!lease_ok)nf<=1;
    else begin closed<=0;bg_closed295<=0;end
   end
   if((state==READY||state==RUN||state==ENDING)&&!lease_ok)nf<=1;
   case(state)
    WAIT:if(word_valid)begin
     if(closed||retire_valid)nf<=1;
     at<=0;length<=16;bad<=0;alt_index<=0;reader<=word[15];batch_length<=word[14:5];remaining<=word[4:0];
     for(i=0;i<8;i=i+1)alt[i]<=0;
     state<=READ;
    end
    READ:begin
     if(read_cursor314>=batch_length||remaining==0||remaining>16)nf<=1;
     else if(at>=16&&alt_index>=8)nf<=1;
     else if(at>=16&&!plan_alt_mask[alt_index])alt_index<=alt_index+1'b1;
     else state<=CAPTURE;
    end
    CAPTURE:begin
     if(at==0&&data[7])begin
      shortform<=1;plan_kind<=data[1:0];partial295<=data==8'h87;if(data[6:2]!=0&&data!=8'h87)bad<=1;
      length<=data[1]?6'd3:data[0]?6'd8:6'd7;
      plan_alt_mask<=0;plan_slot<=0;plan_tag<=0;
      plan_mask<=data[1]?8'd0:8'hff;plan_rows<=data[1]?48'd0:48'hff6b646d2240;
     end else if(shortform&&at!=0)begin
      case(at)
       1:plan_generation[7:0]<=data;2:plan_generation[15:8]<=data;
       3:plan_slot[7:0]<=data;
       4:begin plan_slot[9:8]<=data[1:0];if(data[7:2]!=0)bad<=1;end
       5:plan_tag[7:0]<=data;
       6:begin plan_tag[12:8]<=data[4:0];if(data[7:5]!=0)bad<=1;end
       7:plan_mask<=data;
      endcase
     end else begin
     case(at)
      0:begin plan_kind<=data[1:0];shortform<=0;partial295<=0;if(data[7:2]!=0)bad<=1;end
      1:begin plan_alt_mask<=data;length<=16+{popcount(data),1'b0};end
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
     end
     if(at==length-1)state<=CHECK;else begin at<=at+1'b1;state<=READ;end
    end
    CHECK:if(!shape_ok||!lease_ok||(bg_closed295&&(partial295||plan_kind==0||plan_kind==2)))nf<=1;else state<=plan_kind==3?ENDING:READY;
    READY:if(plan_valid&&plan_ready)state<=RUN;
    RUN:if(tile_done)begin
     if(remaining==1)state<=WAIT;
     else begin
      remaining<=remaining-1'b1;at<=0;length<=16;bad<=0;alt_index<=0;
      for(i=0;i<8;i=i+1)alt[i]<=0;
      state<=READ;
     end
    end
    ENDING:if(end_valid&&end_ready)begin state<=WAIT;if(partial295)bg_closed295<=1;else closed<=1;end
   endcase
  end
 end
endmodule
