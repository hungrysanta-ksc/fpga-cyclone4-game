// Conditional 84MHz SRAM pin engine. A grant reserves eight bus clocks with
// no foreground read. Grant generation/SNES timing is OUTSIDE this module.
// Two clocks release the RAM output driver, four pulse WE, one holds data,
// and one releases the FPGA driver before handing the pins back to the reader.
module sram_granted_writer(
 input wire clk,reset,grant,foreground_read,
 input wire write_valid,input wire[15:0]write_addr,input wire[7:0]write_data,
 output wire write_done,output reg using_write=0,output reg slot_violation=0,
 input wire[18:0]foreground_addr,output wire[7:0]foreground_data,
 output reg[18:0]ram_addr=0,output wire ram_oe,ram_we,inout wire[7:0]ram_data
);
 reg[1:0]reset_pipe;
 always @(posedge clk or posedge reset)
  if(reset)reset_pipe<=3;else reset_pipe<={reset_pipe[0],1'b0};
 reg[3:0]state=0;reg[15:0]held_addr=0;reg[7:0]held_data=0;
 reg we_reg=1,oe_reg=1,drive_reg=0,reset_seen=0;
 // The local pipe asserts asynchronously and releases on this bus clock.
 // A raw reset bypass here would create source-clock paths into bus logic.
 wire inactive=reset_pipe[1];
 assign write_done=state==9&&!inactive&&!slot_violation;
 wire begin_write=state==0&&grant&&write_valid&&!foreground_read&&!slot_violation;
 assign ram_oe=oe_reg;
 assign ram_we=we_reg;
 assign ram_data=drive_reg?held_data:8'hzz;
 assign foreground_data=ram_data;
 // Registered pad controls avoid both decoder glitches and long LUT-to-pad
 // paths. Foreground address/OE now have one bus-clock acquisition latency.
 always @(posedge clk or posedge inactive)begin
  if(inactive)begin we_reg<=1;oe_reg<=1;end
  else begin
   oe_reg<=using_write||begin_write||!foreground_read;
   if(state==2)we_reg<=0;
   if(state==6)we_reg<=1;
  end
 end
 always @(posedge clk)begin
  if(!inactive)begin
   if(begin_write)ram_addr<={3'b0,write_addr};
   else if(!using_write)ram_addr<=foreground_addr;
  end
 end
 // Asynchronous reset immediately raises WE/OE, but must not change address
 // or data at that edge. Keep both for at least one FULL bus clock after the
 // first observed reset edge, even when a reset pulse occurs with clk stopped.
 always @(posedge clk)begin
  reset_seen<=inactive;
  if(inactive)begin
   state<=0;slot_violation<=0;
   if(reset_seen)begin using_write<=0;drive_reg<=0;end
  end
  else begin
   if(using_write&&foreground_read)slot_violation<=1;
   case(state)
    0:if(grant&&write_valid&&!foreground_read&&!slot_violation)begin
     held_addr<=write_addr;held_data<=write_data;using_write<=1;state<=1;
    end
    2:begin state<=3;drive_reg<=1;end
    6:begin state<=7;end
    7:begin state<=8;drive_reg<=0;end
    8:begin state<=9;using_write<=0;end
    9:state<=0; // Upstream observes write_done on this edge, then withdraws valid.
    default:state<=state+1'b1;
   endcase
  end
 end
endmodule
