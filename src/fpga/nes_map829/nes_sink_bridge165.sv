// SPDX-License-Identifier: MIT
// Common host-clock bridge; common reset only, never reset the two halves alone.
module nes_sink_bridge165(
 input wire clk,raw_reset,active,stop,
 output wire session_release_reset,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire spi_selected,spi_miso,
 input wire [23:0] address,input wire read_n,write_n,romsel_n,input wire [7:0] data_in,
 output wire [7:0] data_out,output wire oe_n,dir,
 output wire pad_commit,output wire [15:0] pad_buttons,output wire fault
);
 // RUN loss starts a new transport lifetime, even with a stopped host clock.
 wire raw_cancel=raw_reset||!active;
 wire reset;nes_domain_reset124 release_local(.clk(clk),.raw_reset(raw_cancel),.reset(reset));
 assign session_release_reset=reset;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] idle_ss,idle_write;
 reg host_ready;
 always @(posedge clk or posedge reset)begin
  if(reset)begin idle_ss<=0;idle_write<=0;host_ready<=0;end
  else begin
   idle_ss<={idle_ss[0],SPI_SS};idle_write<={idle_write[0],write_n};
   // Do not join the middle of an old SPI transaction or SNES write.
   // Once admitted, normal activity does not revoke ownership.
   if(!reset&&idle_ss[1]&&idle_write[1])host_ready<=1;
  end
 end
 wire session_reset=reset||!host_ready;
 wire completed_read,completed_valid;wire [7:0] completed_address;
 wire ready,aw,ap,mp;wire [8:0] length;wire [7:0] pa,pd,ab;wire [3:0] ai;
 nes_sink_spi165 endpoint(.clk(clk),.reset(session_reset),.enable(host_ready),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(spi_selected),.miso(spi_miso),.completed_read(completed_read),.completed_valid(completed_valid),.completed_address(completed_address),.sn_address(pa),.sn_data(pd),.packet_ready(ready),.packet_length(length),
  .ack_write(aw),.ack_index(ai),.ack_byte(ab),.ack_publish(ap),.map_progress(mp),.stop(stop),.fault(fault));
 wire bus_oe,bus_dir;
 nes_sink_bus165 bus(.clk(clk),.reset(session_reset),.active(host_ready),.stop(stop),.fault(fault),
  .address(address),.read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.data_in(data_in),
  .data_out(data_out),.oe_n(bus_oe),.dir(bus_dir),.packet_ready(ready),.packet_length(length),.packet_data(pd),.packet_address(pa),.completed_read(completed_read),.completed_valid(completed_valid),.completed_address(completed_address),
  .ack_write(aw),.ack_index(ai),.ack_byte(ab),.ack_publish(ap),.map_progress(mp),.pad_commit(pad_commit),.pad_buttons(pad_buttons));
 assign oe_n=raw_cancel?1'b1:bus_oe;
 assign dir=!raw_cancel&&bus_dir;
endmodule
