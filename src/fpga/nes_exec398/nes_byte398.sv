// SPDX-License-Identifier: MIT
// Byte control interpreter. Memory and IO are explicit request/response ports;
// no asynchronous register-file aliases or second semantic FSM are hidden here.
module nes_byte398 #(parameter PC_BITS=12,parameter ENTRY=0,parameter IRQ_ENTRY=0)(
 input wire clk,reset,stop,input wire irq,
 output wire [PC_BITS-1:0] code_address,input wire [17:0] code_data,input wire code_ready,
 output wire mem_valid,mem_write,output wire [7:0] mem_address,mem_data,
 input wire mem_ready,input wire [7:0] mem_q,
 output wire io_valid,io_write,output wire [7:0] io_address,io_data,
 input wire io_ready,input wire [7:0] io_q,
 output reg fault,output wire in_irq,output wire [PC_BITS-1:0] debug_pc);
 reg [PC_BITS-1:0] pc,return_pc,irq_return_pc,saved_pc;reg[17:0] instruction;
 reg [7:0] acc,saved_acc,index,saved_index;reg carry,zero,saved_carry,saved_zero,handler,atomic;
 localparam FETCH=0,CAPTURE=1,EXECUTE=2,MEMORY=3,IO=4;
 reg [2:0] phase;wire[3:0] op=instruction[17:14];wire [8:0] sum={1'b0,acc}+{1'b0,mem_q}+instruction[8]*carry;
 wire [8:0] difference={1'b0,acc}+{1'b0,~mem_q}+(instruction[8]?carry:1'b1);
 wire [8:0] immediate_compare={1'b0,acc}+{1'b0,~instruction[7:0]}+1'b1;
 wire [8:0] immediate_add={1'b0,acc}+{1'b0,instruction[7:0]};
 wire branch=instruction[13:12]==0||instruction[13:12]==1&&zero||instruction[13:12]==2&&!zero||instruction[13:12]==3&&carry;
 reg [PC_BITS-1:0] next_fetch;
 always @*begin
  next_fetch=pc;
  if(phase==EXECUTE)case(op)
   0,8,9:next_fetch=pc+1'b1;
   12:next_fetch=branch?instruction[PC_BITS-1:0]:pc+1'b1;
   13:next_fetch=instruction[PC_BITS-1:0];14:next_fetch=handler?irq_return_pc:return_pc;
   15:next_fetch=instruction[13:0]==0?saved_pc:pc+1'b1;
   default:;
  endcase
  if(phase==MEMORY&&mem_ready||phase==IO&&io_ready)next_fetch=pc+1'b1;
  if(phase==FETCH&&irq&&!handler&&!atomic)next_fetch=IRQ_ENTRY;
 end
 assign code_address=next_fetch;assign debug_pc=pc;assign in_irq=handler;
 assign mem_valid=!reset&&!stop&&!fault&&phase==MEMORY;
 assign mem_write=op==2;assign mem_address=instruction[9]?index:instruction[7:0];assign mem_data=acc;
 assign io_valid=!reset&&!stop&&!fault&&phase==IO;
 assign io_write=op==11;assign io_address=instruction[9]?index:instruction[7:0];assign io_data=acc;
 task advance;begin pc<=pc+1'b1;phase<=FETCH;end endtask
 always @(posedge clk or posedge reset)begin
  if(reset)begin pc<=ENTRY;phase<=FETCH;acc<=0;index<=0;saved_index<=0;carry<=0;zero<=1;handler<=0;atomic<=0;fault<=0;return_pc<=0;irq_return_pc<=0;saved_pc<=0;saved_acc<=0;saved_carry<=0;saved_zero<=0;instruction<=0;end
  else if(stop)begin fault<=1;end
  else if(!fault)case(phase)
   FETCH:if(irq&&!handler&&!atomic)begin saved_pc<=pc;saved_acc<=acc;saved_index<=index;saved_carry<=carry;saved_zero<=zero;pc<=IRQ_ENTRY;handler<=1;end else if(code_ready)begin instruction<=code_data;phase<=EXECUTE;end
   CAPTURE:phase<=FETCH;
   EXECUTE:case(op)
    0:begin acc<=instruction[7:0];zero<=instruction[7:0]==0;advance();end
    1,2,3,4,5,6,7:phase<=MEMORY;
    8:begin
     if(instruction[0])begin carry<=acc[0];acc<={instruction[1]&&carry,acc[7:1]};zero<={instruction[1]&&carry,acc[7:1]}==0;end
     else begin carry<=acc[7];acc<={acc[6:0],instruction[1]&&carry};zero<={acc[6:0],instruction[1]&&carry}==0;end
     advance();
    end
    9:begin carry<=immediate_compare[8];zero<=immediate_compare[7:0]==0;advance();end
    10,11:phase<=IO;
    12:begin pc<=branch?instruction[PC_BITS-1:0]:pc+1'b1;phase<=FETCH;end
    13:begin if(handler)irq_return_pc<=pc+1'b1;else return_pc<=pc+1'b1;pc<=instruction[PC_BITS-1:0];phase<=FETCH;end
    14:begin pc<=handler?irq_return_pc:return_pc;phase<=FETCH;end
    15:if(instruction[13:8]!=0)begin
     case(instruction[13:8])
      1:begin acc<=acc&instruction[7:0];zero<=(acc&instruction[7:0])==0;end
      2:begin acc<=acc|instruction[7:0];zero<=(acc|instruction[7:0])==0;end
      3:begin acc<=acc^instruction[7:0];zero<=(acc^instruction[7:0])==0;end
      4:begin acc<=immediate_add[7:0];carry<=immediate_add[8];zero<=immediate_add[7:0]==0;end
      5:begin acc<=immediate_compare[7:0];carry<=immediate_compare[8];zero<=immediate_compare[7:0]==0;end
      6:index<=acc;
      7:begin acc<=index;zero<=index==0;end
      default:fault<=1;
     endcase
     advance();
    end else case(instruction[7:0])
     0:begin if(!handler)fault<=1;else begin pc<=saved_pc;acc<=saved_acc;index<=saved_index;carry<=saved_carry;zero<=saved_zero;handler<=0;phase<=FETCH;end end
     1:begin atomic<=1;advance();end
     2:begin atomic<=0;advance();end
     3:advance();
     default:fault<=1;
    endcase
    default:fault<=1;
   endcase
   MEMORY:if(mem_ready)begin
    case(op)
     1:begin acc<=mem_q;zero<=mem_q==0;end
     3:begin acc<=sum[7:0];carry<=sum[8];zero<=sum[7:0]==0;end
     4:begin acc<=difference[7:0];carry<=difference[8];zero<=difference[7:0]==0;end
     5:begin acc<=acc^mem_q;zero<=(acc^mem_q)==0;end
     6:begin acc<=acc&mem_q;zero<=(acc&mem_q)==0;end
     7:begin acc<=acc|mem_q;zero<=(acc|mem_q)==0;end
     default:;
    endcase
    advance();
   end
   IO:if(io_ready)begin if(!io_write)begin acc<=io_q;zero<=io_q==0;end advance();end
    else if(irq&&!handler&&!atomic)begin
     // A blocked IO instruction has not committed. Retry it after servicing
     // the shared ingress event; credit/DMA waits must not mask SPI forever.
     saved_pc<=pc;saved_acc<=acc;saved_index<=index;saved_carry<=carry;saved_zero<=zero;
     pc<=IRQ_ENTRY;handler<=1;phase<=FETCH;
    end
   default:fault<=1;
  endcase
 end
endmodule
