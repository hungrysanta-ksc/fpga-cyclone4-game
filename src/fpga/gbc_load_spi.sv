// Separate boot stream; legacy SPI receiver remains byte-identical.
module gbc_load_spi(input wire clk,reset,SCK,SSEL,MOSI,mode,
 input wire[15:0]tx_data,output wire MISO,output wire payload,
 output reg rx_valid,output reg[15:0]rx_data,output reg tx_take);
 reg[3:0]bits=0;reg header=1,streaming=0;
 reg[14:0]shift=0;reg[15:0]held=0,tx_latch=0;
 reg rx_toggle=0,tx_toggle=0;
 always @(posedge SCK or posedge SSEL)begin
  if(SSEL)begin bits<=0;header<=1;streaming<=0;end
  else if(header)begin
   bits<=bits+1'b1;
   // Decode the completed command on the first arm bit: no MOSI-to-decode path.
   if(bits==8)streaming<=(shift[7:0]==8'hd1)||(shift[7:0]==8'hd2);
   if(bits==15)begin bits<=0;header<=0;end
  end else bits<=bits+1'b1;
 end
 // Configuration initializes SCK state, as in the legacy receiver. Core reset
 // clears the session; stale toggles are ignored before a new D0 session.
 // Local command decode removes core-clock control from the SCK datapath.
 always @(posedge SCK)if(!SSEL)begin
  shift<={shift[13:0],MOSI};
  if(!header&&streaming)begin
   if(bits==0)begin tx_latch<={tx_data[7:0],tx_data[15:8]};tx_toggle<=!tx_toggle;end
   if(bits==15)begin held<={shift[6:0],MOSI,shift[14:7]};rx_toggle<=!rx_toggle;end
  end
 end
 assign payload=!header&&mode;
 // One arm byte follows RDY. Its final falling edge preloads the first bit.
 // All transmitted bits then change only on SCK falling edges (SPI mode 0).
 reg miso_q=0;
 always @(negedge SCK)if(!SSEL)miso_q<=bits==0?tx_data[7]:tx_latch[15-bits];
 assign MISO=miso_q;
 (* async_reg="true" *)reg[1:0]rs=0,ts=0;
 reg rseen=0,tseen=0;
 always @(posedge clk)begin
  if(reset)begin rs<=0;ts<=0;rseen<=0;tseen<=0;rx_valid<=0;tx_take<=0;rx_data<=0;end
  else begin
   rs<={rs[0],rx_toggle};ts<={ts[0],tx_toggle};rx_valid<=0;tx_take<=0;
   if(rs[1]!=rseen)begin rseen<=rs[1];rx_data<=held;rx_valid<=1;end
   if(ts[1]!=tseen)begin tseen<=ts[1];tx_take<=1;end
  end
 end
endmodule
