// SPDX-License-Identifier: MIT
// H1 diagnostic physical pin shell034. No NES game core or external memory service.
module fxpak_nes_h1_top(
 input wire CLKIN,
 input wire SNES_CIC_CLK,
 input wire[23:0]SNES_ADDR_IN,
 input wire SNES_READ_IN,SNES_WRITE_IN,SNES_ROMSEL_IN,SNES_CPU_CLK_IN,
 input wire SNES_REFRESH,SNES_SYSCLK,
 input wire[7:0]SNES_PA_IN,input wire SNES_PARD_IN,SNES_PAWR_IN,
 inout wire[7:0]SNES_DATA,
 output wire SNES_IRQ,SNES_DATABUS_OE,SNES_DATABUS_DIR,
 input wire SPI_MOSI,input wire SPI_SS,input wire SPI_SCK,inout wire SPI_MISO,
 output wire MCU_RDY,
 output wire[21:0]ROM_ADDR,output wire ROM_1CE,ROM_2CE,ROM_ZZ,
 output wire ROM_OE,ROM_WE,ROM_BHE,ROM_BLE,inout wire[15:0]ROM_DATA,
 output wire[18:0]RAM_ADDR,output wire RAM_OE,RAM_WE,inout wire[7:0]RAM_DATA,
 output wire DAC_MCLK,DAC_LRCK,DAC_SDOUT
);

 wire clock84,locked,spi_miso,spi_drive,run_active,diagnostic_fault;
 wire [15:0] epoch;
 wire [7:0] snes_data_out;
 gbc_bus_pll0 pll(.areset(1'b0),.inclk0(CLKIN),.c0(clock84),.locked(locked));
 nes_h1_board_bus boundary(.clock84(clock84),.locked(locked),
  .SPI_MOSI(SPI_MOSI),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.spi_miso(spi_miso),.spi_drive(spi_drive),
  .SNES_ADDR_IN(SNES_ADDR_IN),.SNES_READ_IN(SNES_READ_IN),.SNES_WRITE_IN(SNES_WRITE_IN),
  .SNES_ROMSEL_IN(SNES_ROMSEL_IN),.snes_data_in(SNES_DATA),.snes_data_out(snes_data_out),
  .SNES_DATABUS_OE(SNES_DATABUS_OE),.SNES_DATABUS_DIR(SNES_DATABUS_DIR),
  .run_active(run_active),.epoch(epoch),.diagnostic_fault(diagnostic_fault));
 assign SPI_MISO=spi_drive?spi_miso:1'bz;
 assign SNES_DATA=SNES_DATABUS_DIR&&!SNES_DATABUS_OE?snes_data_out:8'hzz;
 assign MCU_RDY=locked;
 assign ROM_ADDR=0;assign ROM_1CE=1;assign ROM_2CE=1;assign ROM_ZZ=1;
 assign ROM_OE=1;assign ROM_WE=1;assign ROM_BHE=1;assign ROM_BLE=1;assign ROM_DATA=16'hzzzz;
 assign RAM_ADDR=0;assign RAM_OE=1;assign RAM_WE=1;assign RAM_DATA=8'hzz;
 assign DAC_MCLK=0;assign DAC_LRCK=0;assign DAC_SDOUT=0;assign SNES_IRQ=0;
endmodule
