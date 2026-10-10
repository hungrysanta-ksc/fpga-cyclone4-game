// SPDX-License-Identifier: MIT
// Minimum RUN diagnostic shell. SNES stays reset under MCU ownership.
// No SNES program ROM/video/input/audio consumer is enabled in this candidate.
module fxpak_nes_run134_top(
 input wire CLKIN,SNES_SYSCLK,
 input wire SPI_MOSI,SPI_SS,SPI_SCK,inout wire SPI_MISO,
 output wire MCU_RDY,
 inout wire [7:0] SNES_DATA,
 output wire SNES_IRQ,SNES_DATABUS_OE,SNES_DATABUS_DIR,
 output wire [21:0] ROM_ADDR,output wire ROM_1CE,ROM_2CE,ROM_ZZ,
 output wire ROM_OE,ROM_WE,ROM_BHE,ROM_BLE,inout wire [15:0] ROM_DATA,
 output wire [18:0] RAM_ADDR,output wire RAM_OE,RAM_WE,inout wire [7:0] RAM_DATA,
 output wire DAC_MCLK,DAC_LRCK,DAC_SDOUT
);
 // FPGA configuration initializes this shift register. No external reset pin
 // is invented; STOP retains observer state, reconfiguration starts a new run.
 reg [3:0] power_release=0;
 always @(posedge CLKIN)power_release<={power_release[2:0],1'b1};
 wire power_reset=!power_release[3];
 wire observer_reset;
 nes_domain_reset124 observer_release(.clk(SNES_SYSCLK),.raw_reset(power_reset),.reset(observer_reset));
 wire boot_miso,boot_selected,observer_miso,observer_selected;
 wire core_reset,cpu_sample,rom_fault;
 wire [3:0] rom_error;
 nes_live_joint core(
  .ext_clk(SNES_SYSCLK),.CLKIN(CLKIN),.ext_reset(power_reset),.ext_chr32(1'b0),
  .ext_reset_epoch(16'd1),.ext_arm(1'b0),.ext_immutable_chr(1'b1),
  .ext_snes_addr(24'd0),.ext_read_n(1'b1),.ext_write_n(1'b1),.ext_romsel_n(1'b1),.ext_snes_data_in(8'd0),
  .ext_joypad1(5'd0),.ext_joypad2(5'd0),
  .ext_SPI_SS(SPI_SS),.ext_SPI_SCK(SPI_SCK),.ext_SPI_MOSI(SPI_MOSI),
  .out_spi_miso(boot_miso),.out_spi_selected(boot_selected),
  .ext_psram_data(ROM_DATA),.out_psram_address(ROM_ADDR),
  .out_psram_1ce(ROM_1CE),.out_psram_2ce(ROM_2CE),.out_psram_oe(ROM_OE),
  .out_psram_we(ROM_WE),.out_psram_bhe(ROM_BHE),.out_psram_ble(ROM_BLE),
  .out_rom_fault(rom_fault),.out_rom_error_code(rom_error),
  .out_observe_reset(core_reset),.out_observe_sample(cpu_sample),.out_observe_ready(MCU_RDY)
 );
 nes_run_observer134 observer(.clk(SNES_SYSCLK),.reset(observer_reset),
  .core_reset(core_reset),.cpu_sample(cpu_sample),.rom_fault(rom_fault),.rom_error(rom_error),
  .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(observer_selected),.miso(observer_miso));
 // Both slaves release on raw CS. Distinct command ranges60..6A and70.
 // An unexpected overlap fails closed instead of driving ambiguous data.
 assign SPI_MISO=boot_selected&&!observer_selected?boot_miso:
                 observer_selected&&!boot_selected?observer_miso:1'bz;
 assign SNES_DATA=8'hzz;
 assign SNES_DATABUS_OE=1;assign SNES_DATABUS_DIR=0;assign SNES_IRQ=0;
 assign ROM_ZZ=1;
 assign RAM_ADDR=0;assign RAM_OE=1;assign RAM_WE=1;assign RAM_DATA=8'hzz;
 assign DAC_MCLK=0;assign DAC_LRCK=0;assign DAC_SDOUT=0;
endmodule
