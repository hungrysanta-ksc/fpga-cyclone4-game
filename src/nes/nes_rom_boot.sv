// SPDX-License-Identifier: MIT
// Original053 exclusive load/run ownership. Loader controls are memory-clock inputs.
// reset is external/common; read_reset additionally holds052 with the NES core.
module nes_rom_boot(input wire clk,mem_clk,reset,read_reset,
 input wire load_begin,load_chr32,load_valid,load_end,start,stop,input wire [7:0] load_data,
 output wire load_ready,loaded,run_enable,output wire boot_fault,output wire [3:0] boot_error,output wire [16:0] loaded_bytes,
 input wire rom_request,input wire [21:0] rom_address,output wire rom_ready,rom_response,rom_error,
 output wire [21:0] rom_response_address,output wire [7:0] rom_data,
 output wire [21:0] psram_address,output wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,
 inout wire [15:0] psram_data);
 wire [21:0] load_address,read_address;wire [15:0] load_pin_data;wire load_drive;
 wire load_1ce,load_2ce,load_oe,load_we,load_bhe,load_ble;
 wire read_1ce,read_2ce,read_oe,read_we,read_bhe,read_ble;
 nes_rom_loader loader(.mem_clk(mem_clk),.reset(reset),.load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),.load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.fault(boot_fault),.error_code(boot_error),.loaded_bytes(loaded_bytes),.load_address(load_address),.load_pin_data(load_pin_data),.load_drive(load_drive),.load_1ce(load_1ce),.load_2ce(load_2ce),.load_oe(load_oe),.load_we(load_we),.load_bhe(load_bhe),.load_ble(load_ble));
 nes_rom_physical reader(.clk(clk),.mem_clk(mem_clk),.reset(reset || read_reset || !run_enable),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rom_ready),.rom_response(rom_response),.rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .psram_address(read_address),.psram_1ce(read_1ce),.psram_2ce(read_2ce),.psram_oe(read_oe),.psram_we(read_we),.psram_bhe(read_bhe),.psram_ble(read_ble),.psram_data(psram_data));
 assign psram_address=run_enable?read_address:load_address;
 assign psram_1ce=reset?1'b1:run_enable?read_1ce:load_1ce;
 assign psram_2ce=reset?1'b1:run_enable?read_2ce:load_2ce;
 assign psram_oe=reset?1'b1:run_enable?read_oe:load_oe;
 assign psram_we=reset?1'b1:run_enable?read_we:load_we;
 assign psram_bhe=reset?1'b1:run_enable?read_bhe:load_bhe;
 assign psram_ble=reset?1'b1:run_enable?read_ble:load_ble;
 assign psram_data=(!reset && !run_enable && load_drive)?load_pin_data:16'hzzzz;
endmodule
