// SPDX-License-Identifier: MIT
//137 SNES consumer ROM / epoch / existing044 packet bus arbitration.
// Only one80KiB diagnostic image and cold epoch1 are supported.
module nes_screen_bus137(
 input wire host_clk,reset,run_enable,
 input wire [23:0] address,input wire read_n,write_n,romsel_n,
 input wire [7:0] link_data,input wire link_oe_n,link_dir,
 output wire [7:0] data_out,output wire oe_n,dir
);
 (* ramstyle="M9K" *) reg [7:0] program_rom[0:24575];
 initial $readmemh("screen-program.hex",program_rom);
 reg [7:0] rom_data;reg [23:0] rom_address;reg rom_stored;
 wire [14:0] offset=address[14:0];
 wire bank=address[16];
 wire stored=bank ? offset<15'h4000 : offset<15'h1fc0 || offset>=15'h7fc0;
 wire [14:0] index=bank ? 15'h2000+{1'b0,offset[13:0]} :
                               offset>=15'h7fc0 ? 15'h1fc0+{9'd0,offset[5:0]} : offset;
 always @(posedge host_clk)begin
  rom_data<=program_rom[index];rom_address<=address;rom_stored<=stored;
 end
 // Data and transceiver gates cancel on raw control release, as in044.
 wire active=run_enable&&!reset;
 wire raw_read=active&&!read_n&&write_n;
 wire program_select=!address[22]&&address[15]&&!romsel_n;
 wire rom_drive=raw_read&&program_select&&rom_address==address;
 wire epoch_drive=raw_read&&(address==24'h00600b||address==24'h00600c);
 wire link_drive=active&&!link_oe_n&&link_dir;
 wire link_receive=active&&!link_oe_n&&!link_dir;
 assign data_out=rom_drive?(rom_stored?rom_data:8'hff):
                 epoch_drive?(address[0]?8'd1:8'd0):link_data;
 assign dir=rom_drive||epoch_drive||link_drive;
 assign oe_n=!(dir||link_receive);
endmodule
