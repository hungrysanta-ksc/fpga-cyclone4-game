// SPDX-License-Identifier: MIT
// 054 SPI loader + unchanged053 pin ownership. No board clock/consumer binding.
module nes_spi_boot(input wire clk,mem_clk,reset,read_reset,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire spi_miso,spi_selected,
 output wire load_ready,loaded,run_enable,boot_fault,spi_fault,
 output wire [3:0] boot_error,spi_error,output wire [16:0] loaded_bytes,
 input wire rom_request,input wire [21:0] rom_address,output wire rom_ready,rom_response,rom_error,
 output wire [21:0] rom_response_address,output wire [7:0] rom_data,
 output wire [21:0] psram_address,output wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,
 inout wire [15:0] psram_data);
 wire load_begin,load_chr32,load_valid,load_end,start,stop;
 wire [7:0] load_data;wire internal_ready,internal_loaded,internal_run;
 assign load_ready=internal_ready&&!spi_fault;
 assign loaded=internal_loaded&&!spi_fault;
 assign run_enable=internal_run&&!spi_fault;
 nes_rom_spi control(.mem_clk(mem_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .spi_miso(spi_miso),.spi_selected(spi_selected),.load_ready(internal_ready),.loaded(internal_loaded),
  .run_enable(internal_run),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),
  .load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),
  .load_data(load_data),.fault(spi_fault),.error_code(spi_error));
 // Do not reset the loader on a protocol error: an accepted write must drain.
 // A protocol error does immediately cancel the read side and exported RUN.
 nes_rom_boot boot(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(read_reset||spi_fault),
  .load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),
  .load_ready(internal_ready),.loaded(internal_loaded),.run_enable(internal_run),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),
  .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rom_ready),.rom_response(rom_response),.rom_error(rom_error),
  .rom_response_address(rom_response_address),.rom_data(rom_data),.psram_address(psram_address),.psram_1ce(psram_1ce),
  .psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
endmodule
