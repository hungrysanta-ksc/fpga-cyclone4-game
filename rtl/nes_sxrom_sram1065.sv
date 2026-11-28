// Private upper 32 KiB of cartridge SRAM while this NES image owns the bus.
// CPU and checkpoint writes are at least one CPU bus cycle apart. Give each
// byte a full NES clock each of data setup, active write, and hold time.
module nes_sxrom_sram1065(
 input wire clk,reset,wr,
 input wire [14:0] address,input wire [7:0] data_in,
 output wire [7:0] data_out,output reg cleared,
 output wire [18:0] ram_addr,output wire oe_n,we_n,inout wire [7:0] ram_data
);
 localparam IDLE=0, LEAD=1, WRITE=2, HOLD=3;
 reg [1:0] phase;
 reg [14:0] held_address,clear_address;
 reg [7:0] held_data;
 wire driving=phase!=IDLE && !reset;
 assign ram_addr={4'hf,driving?held_address:address};
 assign ram_data=driving?held_data:8'bz;
 assign oe_n=reset || driving;
 assign we_n=reset || phase!=WRITE;
 assign data_out=ram_data;
 always @(posedge clk or posedge reset) begin
   if(reset)begin phase<=IDLE;clear_address<=0;cleared<=0;end
   else case(phase)
     IDLE:if(!cleared || wr)begin
       held_address<=cleared?address:clear_address;
       held_data<=cleared?data_in:8'd0;
       phase<=LEAD;
     end
     LEAD:phase<=WRITE;
     WRITE:phase<=HOLD;
     HOLD:begin
       phase<=IDLE;
       if(!cleared)begin
         if(&clear_address)cleared<=1;
         else clear_address<=clear_address+1'b1;
       end
     end
   endcase
 end
endmodule
