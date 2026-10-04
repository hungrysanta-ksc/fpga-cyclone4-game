// Async SNES pins -> synchronous upload register endpoint.
// Bundled address/data must be stable during /WR. Two sampling stages track
// them alongside /WR; the last low sample is retained before the end pulse.
// This is NOT a general multi-bit CDC synchronizer or an SRAM grant generator.
module snes_regs_pin_bridge(
 input wire clk,reset,input wire[23:0]snes_addr,
 input wire read_n,write_n,input wire[7:0]data_in,
 output wire[7:0]data_out,output wire databus_oe_n,databus_dir,
 output reg host_write,output wire[3:0]host_addr,
 output reg[7:0]host_data,input wire[7:0]host_read_data
);
 (* async_reg="true" *)reg[1:0]wr_sync;
 (* async_reg="true" *)reg[23:0]addr_meta,addr_sync;
 reg[23:0]held_addr;
 (* async_reg="true" *)reg[7:0]data_meta,data_sync;
 reg[7:0]held_data;
 reg wr_previous,held_select;
 wire selected=!snes_addr[22]&&snes_addr[15:4]==12'h600;
 wire reading=!reset&&selected&&!read_n&&write_n&&!host_write;
 wire writing=!reset&&selected&&!write_n&&read_n;
 assign data_out=host_read_data;
 assign databus_dir=reading;
 assign databus_oe_n=!(reading||writing);
 assign host_addr=host_write?held_addr[3:0]:snes_addr[3:0];
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   wr_sync<=3;wr_previous<=1;host_write<=0;host_data<=0;
   addr_meta<=0;addr_sync<=0;data_meta<=0;data_sync<=0;
   held_addr<=0;held_data<=0;held_select<=0;
  end else begin
   wr_sync<={wr_sync[0],write_n};wr_previous<=wr_sync[1];
   addr_meta<=snes_addr;addr_sync<=addr_meta;
   data_meta<=data_in;data_sync<=data_meta;
   host_write<=0;
   if(!wr_sync[1])begin
    held_addr<=addr_sync;held_data<=data_sync;
    held_select<=!addr_sync[22]&&addr_sync[15:4]==12'h600;
   end
   if(!wr_previous&&wr_sync[1]&&held_select)begin
    host_write<=1;host_data<=held_data;
   end
  end
 end
endmodule
