// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Shared byte engine bound by encoder246. One scratch RAM for operands and
// payloads. Host RF access is read-only and only admitted while fully idle.
module nes_operand246 #(parameter PROGRAM_FILE="operand246.mem")(
 input wire clk,reset,abort_source,lease_ok,start,
 input wire [8:0] entry,input wire [15:0] argument0,argument1,
 output wire start_ready,output reg busy,done,output reg [3:0] fault,
 output reg [7:0] result,record_length,output reg record_valid,input wire record_ready,
 input wire rf_read, payload_valid,payload_write,input wire [8:0] payload_address,
 input wire [7:0] payload_data,output wire payload_ready,
 output reg payload_read_valid,output reg [7:0] payload_q,
 output reg byte_valid,input wire byte_ready,output reg [7:0] byte_data
);
 localparam HALT=0,LDI=1,LD=2,ST=3,ADD=4,ADC=5,ADDI=6,ADCI=7,
            ARG=8,XOR_RF=9,ANDI=10,OUT=11,JMP=12,FAIL=13,CMP=14,JZ=15,JC=16,CMPI=17,CMPARG=18,ADDR=19,LDP=20,STP=21,INCADDR=22,
            TEMP=23,LDTEMP=24,GETADDR=25,RECORD=26,ROWPAIR=27,ROWRESULT=28,ROWSCALE=29,SETARG=30;
 localparam FETCH=0,EXEC=1,READ=2,PAIRNEW=3,PAIRMASK=4,PAIRWRITE=5;
 (* ramstyle="M9K" *) reg [7:0] scratch[0:511];
 (* romstyle="M9K" *) reg [17:0] program_rom[0:511];
 initial $readmemb(PROGRAM_FILE,program_rom);
 reg [17:0] instruction;
 reg [8:0] pc;
 reg [2:0] phase;
 reg [6:0] row_i;reg [7:0] old1,old2,new1,new2;reg [2:0] row_flags;
 reg [7:0] accumulator,operand_q,temporary;
 reg [8:0] data_address;
 reg carry,zero;
 reg [15:0] arg0,arg1;
 wire [4:0] opcode=instruction[17:13];
 wire [4:0] index=instruction[4:0];
 wire indirect=opcode==LDP||opcode==STP;
 wire row_instruction=opcode==ROWPAIR;
 wire [8:0] operand_address=row_instruction?
   (phase==READ?9'd128+row_i:(phase==PAIRNEW||phase==PAIRMASK||phase==PAIRWRITE)?9'd96+row_i:{2'b00,row_i}):
   indirect?data_address:{4'b0011,index};
 wire [2:0] map_flags=row_flags & {row_i<2||operand_q==old2,row_i<2||temporary==new2,temporary==operand_q};
 wire mask_same=row_flags[0]&&(temporary==operand_q);
 wire mask_nonzero=row_flags[0]||(temporary!=0);
 wire live=!reset&&!abort_source&&!fault&&lease_ok;
 wire row_write=live&&busy&&row_instruction&&instruction[1:0]==2&&phase==PAIRWRITE;
 wire data_allowed=data_address<104||data_address>=128;
 wire operand_instruction=opcode==LD||opcode==ST||opcode==ADD||opcode==ADC||opcode==XOR_RF||opcode==CMP;
 wire operand_write=live&&busy&&phase==EXEC&&((opcode==ST&&index>=8)||(opcode==STP&&data_allowed));
 wire payload_allowed=payload_address<104||payload_address>=128||(rf_read&&!payload_write&&!busy&&!byte_valid&&!record_valid);
 wire collision=(busy&&indirect&&(phase==EXEC||phase==READ)&&data_address==payload_address&&(payload_write||opcode==STP))||(row_write&&payload_address==operand_address);
 // Literal and cheap storage is owned for the entire operation, not just
 // its individual RAM cycles. Future bytes must not change while OUT stalls.
 wire owned_payload=busy&&payload_write&&((payload_address<66)||(payload_address>=96&&payload_address<104)||(payload_address>=128&&payload_address<194)||(payload_address>=80&&payload_address<92)||(payload_address>=256&&payload_address<496));
 assign payload_ready=live&&payload_allowed&&!collision&&!owned_payload;
 assign start_ready=live&&!busy&&!byte_valid&&!record_valid;
 // RF addresses are protected. B wins any indirect read/write collision;
 // A is backpressured until safe. Concurrent nonconflicting payload access is allowed.
 // Neither RAM port resets contents. External callers own payload lifetime.
 always @(posedge clk)begin
  payload_q<=scratch[payload_address];
  if(payload_valid&&payload_ready&&payload_write)scratch[payload_address]<=payload_data;
 end
 always @(posedge clk)begin
  operand_q<=scratch[operand_address];
  if(operand_write)scratch[operand_address]<=accumulator;
  if(row_write)scratch[operand_address]<=temporary;
 end
 always @(posedge clk)instruction<=program_rom[pc];
 reg [7:0] alu_rhs;
 reg alu_cin,subtract;
 always @*begin
  alu_rhs=(opcode==ADDI||opcode==ADCI||opcode==CMPI)?instruction[7:0]:
          opcode==CMPARG?(instruction[0]?arg1[7:0]:arg0[7:0]):operand_q;
  subtract=opcode==CMP||opcode==CMPI||opcode==CMPARG;
  alu_cin=subtract||((opcode==ADC||opcode==ADCI)&&carry);
 end
 wire [8:0] sum={1'b0,accumulator}+{1'b0,(alu_rhs^{8{subtract}})}+alu_cin;
 task advance;begin pc<=pc+1'b1;phase<=FETCH;end endtask
 always @(posedge clk)begin
  if(reset)begin
   busy<=0;done<=0;fault<=0;byte_valid<=0;byte_data<=0;payload_read_valid<=0;
   pc<=0;phase<=FETCH;accumulator<=0;carry<=0;zero<=0;arg0<=0;arg1<=0;
   row_i<=0;old1<=0;old2<=0;new1<=0;new2<=0;row_flags<=0;
   data_address<=0;temporary<=0;result<=0;record_length<=0;record_valid<=0;
  end else begin
   done<=0;payload_read_valid<=payload_valid&&payload_ready&&!payload_write;
   if(byte_valid&&byte_ready)byte_valid<=0;
   // First fault is sticky, including an abort after an earlier failure.
   if(!fault&&(abort_source||(!lease_ok&&(busy||byte_valid||record_valid))))begin
    fault<=abort_source?4'd4:4'd2;busy<=0;byte_valid<=0;record_valid<=0;
   end else if(!fault&&live)begin
    if(start&&start_ready)begin
     busy<=1;row_i<=0;pc<=entry;phase<=FETCH;arg0<=argument0;arg1<=argument1;
    end else if(busy)begin
     case(phase)
      FETCH:phase<=EXEC;
      EXEC:begin
       if((operand_instruction&&index<8)||(indirect&&!data_allowed)||(opcode==INCADDR&&data_address==511))begin fault<=6;busy<=0;byte_valid<=0;record_valid<=0;end
       else case(opcode)
        ROWPAIR:begin
         if(instruction[12:0]>2)begin fault<=6;busy<=0;byte_valid<=0;record_valid<=0;end
         else begin if(row_i==0)row_flags<=instruction[1:0]==2?0:7;phase<=READ;end
        end
        ROWSCALE:begin accumulator<=instruction[0]?{5'b0,accumulator[7:5]}:{accumulator[4:0],3'b0};advance();end
        ROWRESULT:begin accumulator<={5'b0,row_flags};advance();end
        SETARG:begin if(instruction[0])arg1[7:0]<=accumulator;else arg0[7:0]<=accumulator;advance();end
        HALT:begin busy<=0;done<=1;result<=accumulator;end
        LDI:begin accumulator<=instruction[7:0];advance();end
        ARG:begin
         case(instruction[1:0])
          0:accumulator<=arg0[7:0];1:accumulator<=arg0[15:8];
          2:accumulator<=arg1[7:0];3:accumulator<=arg1[15:8];
         endcase
         advance();
        end
        ST,STP:advance();
        ADDR:begin data_address<={instruction[0],accumulator};advance();end
        INCADDR:begin data_address<=data_address+1'b1;advance();end
        TEMP:begin temporary<=accumulator;advance();end
        LDTEMP:begin accumulator<=temporary;advance();end
        GETADDR:begin accumulator<=data_address[7:0];advance();end
        CMPI,CMPARG:begin carry<=sum[8];zero<=sum[7:0]==0;advance();end
        RECORD:begin
         if(!record_valid)begin
          if(!byte_valid||byte_ready)begin record_valid<=1;record_length<=accumulator;end
         end
         else if(record_ready)begin record_valid<=0;advance();end
        end
        LD,LDP,ADD,ADC,XOR_RF,CMP:phase<=READ;
        ADDI,ADCI:begin accumulator<=sum[7:0];carry<=sum[8];zero<=sum[7:0]==0;advance();end
        ANDI:begin accumulator<=accumulator&instruction[7:0];advance();end
        OUT:if(!byte_valid||byte_ready)begin byte_data<=accumulator;byte_valid<=1;advance();end
        JMP:begin pc<=instruction[8:0];phase<=FETCH;end
        JZ:begin pc<=zero?instruction[8:0]:pc+1'b1;phase<=FETCH;end
        JC:begin pc<=carry?instruction[8:0]:pc+1'b1;phase<=FETCH;end
        default:begin fault<=6;busy<=0;byte_valid<=0;record_valid<=0;end
       endcase
      end
      READ:if(row_instruction)begin temporary<=operand_q;phase<=PAIRNEW;end else begin
       case(opcode)
        LD,LDP:accumulator<=operand_q;
        XOR_RF:accumulator<=accumulator^operand_q;
        CMP:begin carry<=sum[8];zero<=sum[7:0]==0;end
        default:begin accumulator<=sum[7:0];carry<=sum[8];zero<=sum[7:0]==0;end
       endcase
       advance();
      end
      PAIRNEW:begin
       if(instruction[1:0]==0)begin
        row_flags<=map_flags;old2<=old1;old1<=temporary;new2<=new1;new1<=operand_q;
        if(row_i==65)begin accumulator<={5'b0,map_flags};row_i<=0;advance();end
        else begin row_i<=row_i+1'b1;phase<=EXEC;end
       end else begin temporary<=temporary^operand_q;phase<=instruction[1:0]==1?PAIRMASK:PAIRWRITE;end
      end
      PAIRMASK,PAIRWRITE:begin
       row_flags<={2'b0,phase==PAIRMASK?mask_same:mask_nonzero};
       if(row_i==7)begin accumulator<={7'b0,phase==PAIRMASK?mask_same:mask_nonzero};row_i<=0;advance();end
       else begin row_i<=row_i+1'b1;phase<=EXEC;end
      end
      default:begin fault<=6;busy<=0;byte_valid<=0;record_valid<=0;end
     endcase
    end
   end
  end
 end
endmodule
