// SPDX-License-Identifier: MIT
// Compare the actual B-bus writes with independently admitted map literals.
// All transaction strobes here are synchronous to the 84 MHz sink clock.
module nes_map_watch762(
 input wire clk, reset, stop,
 input wire begin_frame, target_bank, literal, invalidate, flush, reference_busy,
 input wire [11:0] reference_address, input wire [7:0] reference_byte,
 input wire arm_low, arm_high, consume, input wire [7:0] command_byte,
 input wire beat, input wire [23:0] source_address, input wire source_read,
 input wire [7:0] peripheral, wire_byte,
 output wire listening, output wire passed, output wire failed, output reg seal_block
);
 // A checked 64-byte row is published only at its last literal byte.
 // Source packets are validated by the E1 endpoint; malformed ingress is fatal.
 reg [63:0] rows;
 (* ramstyle="M9K" *) reg [7:0] expected [0:4095];
 reg [7:0] compare_byte, observed;
 reg [15:0] cursor;
 reg [7:0] low;
 reg low_valid, active, pending, terminal, complete, fault, bank;
 reg [10:0] count;
 wire blocked=reset||stop||fault;
 assign listening=active&&!blocked;
 assign passed=complete&&!blocked&&!active&&!pending&&!reference_busy;
 assign failed=fault;
 always @(posedge clk)begin
  if(literal&&!blocked)expected[reference_address]<=reference_byte;
  compare_byte<=expected[cursor[11:0]];
 end
 always @(posedge clk)begin
  if(reset||stop)begin
   seal_block<=1;rows<=0;bank<=0;low_valid<=0;active<=0;pending<=0;complete<=0;fault<=0;
   cursor<=0;count<=0;terminal<=0;low<=0;observed<=0;
  end else if(!fault)begin
   pending<=0;
   if(consume)begin
    complete<=0;
    if(!passed)fault<=1;
    else seal_block<=0;
   end
   if(begin_frame)begin
    if(active||pending||low_valid||complete)fault<=1;
    rows<=0;complete<=0;bank<=target_bank;seal_block<=0;
   end
   if(literal && reference_address[5:0]==63)rows[reference_address[11:6]]<=1;
   if(invalidate)rows[reference_address[11:6]]<=0;
   if(flush)rows<=0;
   if((active||pending||complete)&&(literal||invalidate||flush))fault<=1;
   if(arm_low)begin
    if(active||pending||low_valid)fault<=1;
    seal_block<=1;complete<=0;low<=command_byte;low_valid<=1;
   end
   if(arm_high)begin
    if(!low_valid||command_byte[7:4]!={bank,3'b101}||low[5:0]!=0||
       {command_byte[3:0],low}>12'ha00)fault<=1;
    low_valid<=0;cursor<={command_byte,low};count<=0;active<=1;
   end
   if(complete&&beat&&source_read&&source_address[23:16]==8'h7f&&peripheral[7:1]==7'h0c)fault<=1;
   if(beat&&active)begin
    if(!source_read||source_address!={8'h7f,cursor}||
       peripheral!={7'h0c,count[0]}||!rows[cursor[11:6]])fault<=1;
    observed<=wire_byte;pending<=1;terminal<=count==1535;
    cursor<=cursor+1'b1;count<=count+1'b1;
    if(count==1535)active<=0;
   end
   if(pending)begin
    if(compare_byte!=observed)fault<=1;
    else if(terminal)complete<=1;
   end
  end
 end
endmodule
