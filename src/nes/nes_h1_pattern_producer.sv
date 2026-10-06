// SPDX-License-Identifier: MIT
// Diagnostic-only 3-page ROM producer. Not a live NES frame encoder.
module nes_h1_pattern_producer #(parameter PATTERN_FILE="h1-pattern.hex")(
 input wire queue_clk,reset,
 input wire [15:0] reset_epoch,
 output reg [1:0] p_op,
 output wire [15:0] p_epoch,p_seq,
 output wire [11:0] p_length,
 output wire [7:0] p_data,
 input wire p_accept,
 input wire [3:0] p_error,
 output reg producer_fault,exhausted,
 output reg [3:0] producer_error,
 output reg [15:0] published
);
 localparam BOOT=0,BEGIN_SEND=1,BEGIN_WAIT=2,ROM_WAIT=3,WRITE_SEND=4,WRITE_WAIT=5,PUBLISH_SEND=6,PUBLISH_WAIT=7,STOP=8;
 reg [3:0] state;
 reg [2:0] boot_count;
 reg [7:0] watchdog;
 reg [15:0] epoch_q,sequence_q;
 reg [1:0] page;
 reg [10:0] offset;
 (* ramstyle="M9K" *) reg [7:0] pattern[0:6143];
 reg [7:0] rom_q;
 wire [12:0] rom_address={page,offset};
 initial $readmemh(PATTERN_FILE,pattern);
 always @(posedge queue_clk) rom_q<=pattern[rom_address];
 assign p_epoch=epoch_q;
 assign p_seq=sequence_q;
 assign p_length=12'd2048;
 assign p_data=rom_q;
 always @(posedge queue_clk or posedge reset) begin
  if(reset) begin
   state<=BOOT;boot_count<=0;p_op<=0;epoch_q<=0;sequence_q<=1;
   page<=0;offset<=0;watchdog<=0;producer_fault<=0;producer_error<=0;
   exhausted<=0;published<=0;
  end else begin
   p_op<=0;
   case(state)
    BOOT:begin
     epoch_q<=reset_epoch;
     if(boot_count==7)state<=BEGIN_SEND;else boot_count<=boot_count+1'b1;
    end
    BEGIN_SEND:begin p_op<=1;watchdog<=0;state<=BEGIN_WAIT;end
    BEGIN_WAIT:begin
     if(p_accept)begin offset<=0;state<=ROM_WAIT;end
     else if(p_error==1)state<=BEGIN_SEND; // Both slots held: retry same sequence/page.
     else if(p_error!=0)begin producer_fault<=1;producer_error<=p_error;state<=STOP;end
     else if(watchdog==255)begin producer_fault<=1;producer_error<=15;state<=STOP;end
     else watchdog<=watchdog+1'b1;
    end
    ROM_WAIT:state<=WRITE_SEND;
    WRITE_SEND:begin p_op<=2;watchdog<=0;state<=WRITE_WAIT;end
    WRITE_WAIT:begin
     if(p_accept)begin
      if(offset==2047)state<=PUBLISH_SEND;
      else begin offset<=offset+1'b1;state<=ROM_WAIT;end
     end else if(p_error!=0 || watchdog==255)begin
      producer_fault<=1;producer_error<=p_error==0?4'd15:p_error;state<=STOP;
     end else watchdog<=watchdog+1'b1;
    end
    PUBLISH_SEND:begin p_op<=3;watchdog<=0;state<=PUBLISH_WAIT;end
    PUBLISH_WAIT:begin
     if(p_accept)begin
      published<=sequence_q;
      if(sequence_q==65535)begin exhausted<=1;state<=STOP;end
      else begin sequence_q<=sequence_q+1'b1;page<=page==2?0:page+1'b1;state<=BEGIN_SEND;end
     end else if(p_error!=0 || watchdog==255)begin
      producer_fault<=1;producer_error<=p_error==0?4'd15:p_error;state<=STOP;
     end else watchdog<=watchdog+1'b1;
    end
    STOP:p_op<=0;
    default:begin producer_fault<=1;producer_error<=15;state<=STOP;end
   endcase
  end
 end
endmodule
