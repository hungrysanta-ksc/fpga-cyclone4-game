// SPDX-License-Identifier: MIT
// Common host-clock bridge; common reset only, never reset the two halves alone.
module nes_sink_bridge165(
 input wire clk,raw_reset,active,stop,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire spi_selected,spi_miso,
 input wire [23:0] address,input wire read_n,write_n,romsel_n,input wire [7:0] data_in,
 output wire [7:0] data_out,output wire oe_n,dir,
 output wire pad_commit,output wire [15:0] pad_buttons,output wire fault
);
 wire reset;nes_domain_reset124 release_local(.clk(clk),.raw_reset(raw_reset),.reset(reset));
 wire ready,aw,ap;wire [8:0] length;wire [7:0] pa,pd,ab;wire [3:0] ai;
 nes_sink_spi165 endpoint(.clk(clk),.reset(reset),.enable(active),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(spi_selected),.miso(spi_miso),.sn_address(pa),.sn_data(pd),.packet_ready(ready),.packet_length(length),
  .ack_write(aw),.ack_index(ai),.ack_byte(ab),.ack_publish(ap),.fault(fault));
 wire bus_oe,bus_dir;
 nes_sink_bus165 bus(.clk(clk),.reset(reset),.active(active),.stop(stop),.fault(fault),
  .address(address),.read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.data_in(data_in),
  .data_out(data_out),.oe_n(bus_oe),.dir(bus_dir),.packet_ready(ready),.packet_length(length),.packet_data(pd),.packet_address(pa),
  .ack_write(aw),.ack_index(ai),.ack_byte(ab),.ack_publish(ap),.pad_commit(pad_commit),.pad_buttons(pad_buttons));
 assign oe_n=raw_reset?1'b1:bus_oe;
 assign dir=!raw_reset&&bus_dir;
endmodule
