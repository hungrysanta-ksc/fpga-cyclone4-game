// SPDX-License-Identifier: MIT
//045 original bounded packet-memory reader. Descriptor source owns immutable bytes
//until done/reset. This is NOT a NES pixel encoder or a physical SDRAM controller.
module nes_packet_memory_producer #(parameter integer TIMEOUT_CYCLES=255)(
 input wire queue_clk,reset,
 input wire [15:0] reset_epoch,
 input wire desc_valid,
 output wire desc_ready,
 input wire [15:0] desc_epoch,desc_seq,
 input wire [23:0] desc_base,
 input wire [11:0] desc_length,
 output wire mem_req_valid,
 input wire mem_req_ready,
 output wire [23:0] mem_req_address,
 output wire [15:0] mem_req_epoch,
 input wire mem_rsp_valid,
 output wire mem_rsp_ready,
 input wire [23:0] mem_rsp_address,
 input wire [15:0] mem_rsp_epoch,
 input wire [7:0] mem_rsp_data,
 input wire mem_rsp_error,
 output wire [1:0] p_op,
 output reg [15:0] p_epoch,p_seq,
 output reg [11:0] p_length,
 output reg [7:0] p_data,
 input wire p_accept,
 input wire [3:0] p_error,
 output reg done,producer_fault,exhausted,
 output reg [7:0] producer_error,
 output reg [15:0] published
);
 localparam [3:0] IDLE=0,BEGIN_SEND=1,BEGIN_WAIT=2,MEM_REQ=3,MEM_WAIT=4,
                  WRITE_SEND=5,WRITE_WAIT=6,PUBLISH_SEND=7,PUBLISH_WAIT=8,STOP=9;
 reg [3:0] state;
 reg [23:0] base;
 reg [11:0] offset;
 reg [15:0] next_seq,wait_cycles;
 wire [24:0] descriptor_end={1'b0,desc_base}+{13'b0,desc_length}-25'd1;
 assign desc_ready=!reset && !producer_fault && !exhausted && state==IDLE;
 assign mem_req_valid=!reset && !producer_fault && state==MEM_REQ;
 assign mem_req_address=base+{12'b0,offset};
 assign mem_req_epoch=p_epoch;
 assign mem_rsp_ready=!reset && !producer_fault;
 assign p_op=reset || producer_fault ? 2'd0 : state==BEGIN_SEND ? 2'd1 :
             state==WRITE_SEND ? 2'd2 : state==PUBLISH_SEND ? 2'd3 : 2'd0;
 task automatic fail(input [7:0] code);
  begin producer_fault<=1;producer_error<=code;state<=STOP;end
 endtask
 // Match the synchronous queue reset: capture epoch on queue_clk while reset is held.
 // Output requests are gated immediately by reset, including a stopped clock.
 always @(posedge queue_clk)begin
  if(reset)begin
   state<=IDLE;base<=0;offset<=0;next_seq<=1;wait_cycles<=0;
   p_epoch<=reset_epoch;p_seq<=0;p_length<=0;p_data<=0;
   done<=0;producer_fault<=0;producer_error<=0;published<=0;exhausted<=0;
  end else begin
   done<=0;
   // Stale epochs are drained, never written. A current-epoch unsolicited
   // response fails closed. Service responses must be at least one cycle late.
   if(!producer_fault && mem_rsp_valid && mem_rsp_epoch==p_epoch && state!=MEM_WAIT)
    fail(8'h15);
   else if(!producer_fault)case(state)
    IDLE:if(desc_valid)begin
     if(desc_length==0 || desc_length>3072)fail(8'h01);
     else if(desc_epoch!=p_epoch)fail(8'h02);
     else if(desc_seq==0 || desc_seq!=next_seq || exhausted)fail(8'h03);
     else if(descriptor_end[24])fail(8'h04);
     else begin base<=desc_base;p_seq<=desc_seq;p_length<=desc_length;offset<=0;state<=BEGIN_SEND;end
    end
    BEGIN_SEND:begin state<=BEGIN_WAIT;wait_cycles<=0;end
    BEGIN_WAIT:begin
     if(p_accept)begin state<=MEM_REQ;wait_cycles<=0;end
     else if(p_error==1)state<=BEGIN_SEND; // Backpressure: no memory request yet.
     else if(p_error!=0)fail({4'h2,p_error});
     else if(wait_cycles==TIMEOUT_CYCLES-1)fail(8'h10);
     else wait_cycles<=wait_cycles+1'b1;
    end
    MEM_REQ:begin
     if(mem_req_ready)begin state<=MEM_WAIT;wait_cycles<=0;end
     else if(wait_cycles==TIMEOUT_CYCLES-1)fail(8'h11);
     else wait_cycles<=wait_cycles+1'b1;
    end
    MEM_WAIT:begin
     if(mem_rsp_valid && mem_rsp_epoch==p_epoch)begin
      if(mem_rsp_address!=mem_req_address)fail(8'h13);
      else if(mem_rsp_error)fail(8'h14);
      else begin p_data<=mem_rsp_data;state<=WRITE_SEND;end
     end else if(wait_cycles==TIMEOUT_CYCLES-1)fail(8'h12);
     else wait_cycles<=wait_cycles+1'b1;
    end
    WRITE_SEND:begin state<=WRITE_WAIT;wait_cycles<=0;end
    WRITE_WAIT:begin
     if(p_accept)begin
      if(offset==p_length-1)state<=PUBLISH_SEND;
      else begin offset<=offset+1'b1;state<=MEM_REQ;wait_cycles<=0;end
     end else if(p_error!=0)fail({4'h2,p_error});
     else if(wait_cycles==TIMEOUT_CYCLES-1)fail(8'h10);
     else wait_cycles<=wait_cycles+1'b1;
    end
    PUBLISH_SEND:begin state<=PUBLISH_WAIT;wait_cycles<=0;end
    PUBLISH_WAIT:begin
     if(p_accept)begin
      done<=1;published<=p_seq;
      if(p_seq==65535)begin exhausted<=1;state<=STOP;end
      else begin next_seq<=p_seq+1'b1;state<=IDLE;end
     end else if(p_error!=0)fail({4'h2,p_error});
     else if(wait_cycles==TIMEOUT_CYCLES-1)fail(8'h10);
     else wait_cycles<=wait_cycles+1'b1;
    end
    STOP:state<=STOP;
    default:fail(8'hff);
   endcase
  end
 end
endmodule
