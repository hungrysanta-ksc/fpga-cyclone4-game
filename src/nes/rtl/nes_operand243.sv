// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Candidate shared byte engine, NOT yet bound to encoder240. Scratch is the
// future replacement for its existing scratch M9K, not a second operand RAM.
module nes_operand243 #(parameter PROGRAM_FILE="operand243.mem")(
 input wire clk,reset,abort_source,lease_ok,start,
 input wire [8:0] entry,input wire [15:0] argument0,argument1,
 output wire start_ready,output reg busy,done,output reg [3:0] fault,
 input wire payload_valid,payload_write,input wire [8:0] payload_address,
 input wire [7:0] payload_data,output wire payload_ready,
 output reg payload_read_valid,output reg [7:0] payload_q,
 output reg byte_valid,input wire byte_ready,output reg [7:0] byte_data
);
 localparam HALT=0,LDI=1,LD=2,ST=3,ADD=4,ADC=5,ADDI=6,ADCI=7,
            ARG=8,XOR_RF=9,ANDI=10,OUT=11,JMP=12,FAIL=13,CMP=14,JZ=15,JC=16;
 localparam FETCH=0,EXEC=1,READ=2;
 (* ramstyle="M9K" *) reg [7:0] scratch[0:511];
 (* romstyle="M9K" *) reg [17:0] program_rom[0:511];
 initial $readmemb(PROGRAM_FILE,program_rom);
 reg [17:0] instruction;
 reg [8:0] pc;
 reg [1:0] phase;
 reg [7:0] accumulator,operand_q;
 reg carry,zero;
 reg [15:0] arg0,arg1;
 wire [4:0] opcode=instruction[17:13];
 wire [4:0] index=instruction[4:0];
 wire [8:0] operand_address={4'b0011,index};
 wire live=!reset&&!abort_source&&!fault&&lease_ok;
 wire operand_instruction=opcode==LD||opcode==ST||opcode==ADD||opcode==ADC||opcode==XOR_RF||opcode==CMP;
 wire operand_write=live&&busy&&phase==EXEC&&opcode==ST&&index>=8;
 wire payload_allowed=payload_address<104||payload_address>=128;
 assign payload_ready=live&&payload_allowed;
 assign start_ready=live&&!busy&&!byte_valid;
 // Ports are disjoint by construction: B only104..127; A excludes that range.
 // Neither RAM port resets contents. External callers own payload lifetime.
 always @(posedge clk)begin
  payload_q<=scratch[payload_address];
  if(payload_valid&&payload_ready&&payload_write)scratch[payload_address]<=payload_data;
 end
 always @(posedge clk)begin
  operand_q<=scratch[operand_address];
  if(operand_write)scratch[operand_address]<=accumulator;
 end
 always @(posedge clk)instruction<=program_rom[pc];
 reg [7:0] alu_rhs;
 reg alu_cin,subtract;
 always @*begin
  alu_rhs=(opcode==ADDI||opcode==ADCI)?instruction[7:0]:operand_q;
  subtract=opcode==CMP;
  alu_cin=subtract||((opcode==ADC||opcode==ADCI)&&carry);
 end
 wire [8:0] sum={1'b0,accumulator}+{1'b0,(alu_rhs^{8{subtract}})}+alu_cin;
 task advance;begin pc<=pc+1'b1;phase<=FETCH;end endtask
 always @(posedge clk)begin
  if(reset)begin
   busy<=0;done<=0;fault<=0;byte_valid<=0;byte_data<=0;payload_read_valid<=0;
   pc<=0;phase<=FETCH;accumulator<=0;carry<=0;zero<=0;arg0<=0;arg1<=0;
  end else begin
   done<=0;payload_read_valid<=payload_valid&&payload_ready&&!payload_write;
   if(byte_valid&&byte_ready)byte_valid<=0;
   // First fault is sticky, including an abort after an earlier failure.
   if(!fault&&(abort_source||(!lease_ok&&(busy||byte_valid))))begin
    fault<=abort_source?4'd4:4'd2;busy<=0;byte_valid<=0;
   end else if(!fault&&live)begin
    if(start&&start_ready)begin
     busy<=1;pc<=entry;phase<=FETCH;arg0<=argument0;arg1<=argument1;
    end else if(busy)begin
     case(phase)
      FETCH:phase<=EXEC;
      EXEC:begin
       if(operand_instruction&&index<8)begin fault<=6;busy<=0;byte_valid<=0;end
       else case(opcode)
        HALT:begin busy<=0;done<=1;end
        LDI:begin accumulator<=instruction[7:0];advance();end
        ARG:begin
         case(instruction[1:0])
          0:accumulator<=arg0[7:0];1:accumulator<=arg0[15:8];
          2:accumulator<=arg1[7:0];3:accumulator<=arg1[15:8];
         endcase
         advance();
        end
        ST:advance();
        LD,ADD,ADC,XOR_RF,CMP:phase<=READ;
        ADDI,ADCI:begin accumulator<=sum[7:0];carry<=sum[8];zero<=sum[7:0]==0;advance();end
        ANDI:begin accumulator<=accumulator&instruction[7:0];advance();end
        OUT:if(!byte_valid||byte_ready)begin byte_data<=accumulator;byte_valid<=1;advance();end
        JMP:begin pc<=instruction[8:0];phase<=FETCH;end
        JZ:begin pc<=zero?instruction[8:0]:pc+1'b1;phase<=FETCH;end
        JC:begin pc<=carry?instruction[8:0]:pc+1'b1;phase<=FETCH;end
        default:begin fault<=6;busy<=0;byte_valid<=0;end
       endcase
      end
      READ:begin
       case(opcode)
        LD:accumulator<=operand_q;
        XOR_RF:accumulator<=accumulator^operand_q;
        CMP:begin carry<=sum[8];zero<=sum[7:0]==0;end
        default:begin accumulator<=sum[7:0];carry<=sum[8];zero<=sum[7:0]==0;end
       endcase
       advance();
      end
      default:begin fault<=6;busy<=0;byte_valid<=0;end
     endcase
    end
   end
  end
 end
endmodule
