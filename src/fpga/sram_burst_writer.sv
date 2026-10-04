// Byte (8 clocks) or adjacent little-endian word (14 clocks) reservation.
// Complete is asserted only after both write pulses and bus release finish.
module sram_burst_writer(
 input wire clk,reset,grant,foreground_read,
 input wire write_valid,input wire[15:0]write_addr,write_data,input wire write_word,
 output wire write_done,output reg using_write=0,output reg slot_violation=0,
 input wire[18:0]foreground_addr,output wire[7:0]foreground_data,
 output reg[18:0]ram_addr=0,output wire ram_oe,ram_we,inout wire[7:0]ram_data
);
 (* async_reg="true" *)reg[1:0]reset_pipe;
 always @(posedge clk or posedge reset)
  if(reset)reset_pipe<=3;else reset_pipe<={reset_pipe[0],1'b0};
 wire inactive=reset_pipe[1];
 reg[3:0]state=0;reg[7:0]held_high=0,pad_data=0,data_next=0;reg held_word=0;
 reg[18:0]addr_next=0;
 reg we_reg=1,oe_reg=1,drive_reg=0,drive_next=0,reset_seen=0;
 wire begin_write=state==0&&grant&&write_valid&&!foreground_read&&!slot_violation;
 assign write_done=state==15&&!inactive&&!slot_violation;
 assign ram_oe=oe_reg;assign ram_we=we_reg;
 assign ram_data=drive_reg?pad_data:8'hzz;assign foreground_data=ram_data;
 // Address/data/driver changes trail WE by half a bus cycle. This protects
 // tAH/tDH despite different delays of row and column FPGA output buffers.
 // OE and WE stay on rising edges; their pulse widths are unchanged.
 always @(negedge clk)begin ram_addr<=addr_next;pad_data<=data_next;drive_reg<=drive_next;end
 always @(posedge clk or posedge inactive)begin
  if(inactive)begin we_reg<=1;oe_reg<=1;end
  else begin
   oe_reg<=using_write||begin_write||!foreground_read;
   if(state==2||state==8)we_reg<=0;
   if(state==6||state==12)we_reg<=1;
  end
 end
 always @(posedge clk)begin
  reset_seen<=inactive;
  if(inactive)begin
   state<=0;slot_violation<=0;
   if(reset_seen)begin using_write<=0;drive_next<=0;end
  end else begin
   if(using_write&&foreground_read)slot_violation<=1;
   if(!using_write)addr_next<=foreground_addr;
   case(state)
    0:if(begin_write)begin
     addr_next<={3'b0,write_addr};data_next<=write_data[7:0];held_high<=write_data[15:8];
     held_word<=write_word;using_write<=1;state<=1;
     if(write_word&&write_addr==16'hffff)slot_violation<=1;
    end
    2:begin state<=3;drive_next<=1;end
    6:state<=held_word?7:13;
    7:begin state<=8;addr_next<=addr_next+1'b1;data_next<=held_high;end
    13:begin state<=14;drive_next<=0;end
    14:begin state<=15;using_write<=0;end
    15:state<=0;
    default:state<=state+1'b1;
   endcase
  end
 end
endmodule
