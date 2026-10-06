// SPDX-License-Identifier: MIT
// H1-only board boundary. clock84 and locked come from the physical8MHz ->84MHz PLL.
// SPI mode0 <=250kHz, >=1us between bytes and >=1us SS hold after final rising edge.
module nes_h1_board_bus(
 input wire clock84,locked,
 input wire SPI_MOSI,SPI_SS,SPI_SCK,
 output wire spi_miso,spi_drive,
 input wire [23:0] SNES_ADDR_IN,
 input wire SNES_READ_IN,SNES_WRITE_IN,SNES_ROMSEL_IN,
 input wire [7:0] snes_data_in,
 output wire [7:0] snes_data_out,
 output wire SNES_DATABUS_OE,SNES_DATABUS_DIR,
 output wire run_active,
 output wire [15:0] epoch,
 output wire diagnostic_fault
);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] lock_release=0;
 always @(posedge clock84 or negedge locked)
  if(!locked)lock_release<=0;else lock_release<={lock_release[0],1'b1};
 wire control_reset=!lock_release[1];
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss_sync=3,sck_sync=0,mosi_sync=0;
 reg ss_previous=1,sck_previous=0;
 reg [7:0] shift=0,command=0,key_a=0,key_b=0;
 reg [2:0] bit_count=0;
 reg [2:0] byte_count=0;
 reg running=0;
 reg [15:0] generation=0;
 wire ready,busy,fault,host_read_owned,producer_fault,exhausted;
 wire [3:0] bus_error,frontend_error,producer_error;
 wire [15:0] published;
 wire [7:0] status={3'b0,exhausted,diagnostic_fault,locked,run_active};
 wire [7:0] reply=command==8'hf0 ?8'ha5:command==8'hf1 ?8'h34:
  command==8'hf2 ?status:command==8'hf3 ?generation[7:0]:command==8'hf4 ?generation[15:8]:8'd0;
 assign spi_miso=reply[7-bit_count];
 assign spi_drive=locked&&!control_reset&&!SPI_SS;
 assign epoch=generation;
 // Immediate raw PLL-loss cut works even if clock84 has stopped.
 assign run_active=running&&locked&&!control_reset;
 always @(posedge clock84 or posedge control_reset) begin
  if(control_reset)begin
   ss_sync<=3;sck_sync<=0;mosi_sync<=0;ss_previous<=1;sck_previous<=0;
   shift<=0;command<=0;key_a<=0;key_b<=0;bit_count<=0;byte_count<=0;running<=0;
  end else begin
   ss_sync<={ss_sync[0],SPI_SS};sck_sync<={sck_sync[0],SPI_SCK};mosi_sync<={mosi_sync[0],SPI_MOSI};
   ss_previous<=ss_sync[1];sck_previous<=sck_sync[1];
   if(ss_sync[1])begin
    bit_count<=0;byte_count<=0;
    if(!ss_previous && bit_count==0 && byte_count==3 && key_a==8'ha5 && key_b==8'h5a)begin
     if(command==8'he9)running<=0;
     // No restart while active; generation rollover requires reconfiguration.
     else if(command==8'he8 && !running && generation!=65535)running<=1;
    end
   end else if(sck_sync[1]&&!sck_previous)begin
    shift<={shift[6:0],mosi_sync[1]};bit_count<=bit_count+1'b1;
    if(bit_count==7)begin
     if(byte_count!=7)byte_count<=byte_count+1'b1;
     case(byte_count)
      0:command<={shift[6:0],mosi_sync[1]};
      1:key_a<={shift[6:0],mosi_sync[1]};
      2:key_b<={shift[6:0],mosi_sync[1]};
     endcase
    end
   end
  end
 end
 // Generation is initialized by configuration, retained across PLL loss/STOP.
 always @(posedge clock84)
  if(!control_reset && ss_sync[1]&&!ss_previous && bit_count==0 && byte_count==3 &&
     command==8'he8 && key_a==8'ha5 && key_b==8'h5a && !running && generation!=65535)
   generation<=generation+1'b1;
 wire reset=!run_active;
 wire [7:0] link_data;
 wire link_oe_n,link_dir;
 nes_h1_pattern link(
  .queue_clk(clock84),.host_clk(clock84),.reset(reset),.reset_epoch(generation),
  .snes_addr(SNES_ADDR_IN),.read_n(SNES_READ_IN),.write_n(SNES_WRITE_IN),
  .romsel_n(SNES_ROMSEL_IN),.snes_data_in(snes_data_in),.bus_data(link_data),
  .databus_oe_n(link_oe_n),.databus_dir(link_dir),
  .ready(ready),.busy(busy),.fault(fault),.host_read_owned(host_read_owned),
  .bus_error(bus_error),.frontend_error(frontend_error),
  .producer_fault(producer_fault),.exhausted(exhausted),.producer_error(producer_error),.published(published));
 assign diagnostic_fault=fault||producer_fault||(|bus_error)||(|frontend_error);

 // Compact ROM: first bank0000..31ff plus7fc0..7fff; second bank0000..1fff.
 // Unstored regions return FF; builder verifies the full64KiB image roundtrip.
 (* ramstyle="M9K" *) reg [7:0] program_rom[0:24575];
 initial $readmemh("h1-program.hex",program_rom);
 wire [14:0] rom_offset=SNES_ADDR_IN[14:0];
 wire bank=SNES_ADDR_IN[16];
 wire stored=bank ? rom_offset<15'h2000 : (rom_offset<15'h3200 || rom_offset>=15'h7fc0);
 wire [14:0] rom_index=bank ? (15'h4000+{2'b0,rom_offset[12:0]}) :
   (rom_offset>=15'h7fc0 ? (15'h3fc0+{9'b0,rom_offset[5:0]}) : {1'b0,rom_offset[13:0]});
 reg [7:0] rom_data;
 reg [23:0] rom_address=0;
 reg rom_stored=0;
 always @(posedge clock84)begin
  rom_data<=program_rom[rom_index];rom_address<=SNES_ADDR_IN;rom_stored<=stored;
 end
 wire raw_read=run_active&&!SNES_READ_IN&&SNES_WRITE_IN;
 wire program_select=!SNES_ADDR_IN[22]&&SNES_ADDR_IN[15]&&!SNES_ROMSEL_IN;
 wire rom_drive=raw_read&&program_select&&rom_address==SNES_ADDR_IN;
 wire epoch_select=SNES_ADDR_IN==24'h00600b||SNES_ADDR_IN==24'h00600c;
 wire epoch_drive=raw_read&&epoch_select;
 wire link_drive=run_active&&!link_oe_n&&link_dir;
 wire link_receive=run_active&&!link_oe_n&&!link_dir;
 assign snes_data_out=rom_drive?(rom_stored?rom_data:8'hff):
  epoch_drive?(SNES_ADDR_IN[0]?generation[7:0]:generation[15:8]):link_data;
 assign SNES_DATABUS_DIR=rom_drive||epoch_drive||link_drive;
 assign SNES_DATABUS_OE=!(SNES_DATABUS_DIR||link_receive);
endmodule
