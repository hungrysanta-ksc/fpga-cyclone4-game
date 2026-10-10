// SPDX-License-Identifier: MIT
// Original053 exclusive load/run ownership. Loader controls are memory-clock inputs.
// reset is external/common; read_reset additionally holds052 with the NES core.
module nes_rom_boot(input wire clk,mem_clk,reset,read_reset,
 input wire check_enable,check_request,input wire [16:0] check_address,
 output wire check_ready,check_response,output wire [16:0] check_response_address,
 output wire [7:0] check_data,output wire check_fault,
 input wire load_begin,load_chr32,load_valid,load_end,start,stop,input wire [7:0] load_data,
 output wire load_ready,loaded,run_enable,output wire boot_fault,output wire [3:0] boot_error,output wire [16:0] loaded_bytes,
 output wire rom_chr32,
 input wire rom_request,input wire [21:0] rom_address,output wire rom_ready,rom_response,rom_error,
 output wire [21:0] rom_response_address,output wire [7:0] rom_data,
 output wire [21:0] psram_address,output wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,
 inout wire [15:0] psram_data);
 reg check_failed;
 wire loader_run;
 wire check_active=check_enable && loaded && !loader_run && !boot_fault && !check_failed;
 wire reader_owner=run_enable || check_active;
 wire reader_reset=reset || check_failed || (!check_active && (read_reset || !run_enable));
 wire raw_check_ready,raw_check_response;
 wire [21:0] raw_check_address;
 wire address_valid=check_address < (rom_chr32 ? 17'h18000 : 17'h14000);
 wire [21:0] physical_check_address=check_address[16] ?
     {1'b1,5'b0,check_address[15:0]} : {6'b0,check_address[15:0]};
 assign check_fault=check_failed;
 assign run_enable=loader_run && !check_failed;
 assign check_ready=check_active && raw_check_ready;
 assign check_response=raw_check_response; //128 registered response, canceled by reader_reset
 assign check_response_address={raw_check_address[21],raw_check_address[15:0]};
 always @(posedge mem_clk or posedge reset)
  if(reset)check_failed<=0;
  //135: expand !check_ready and absorb the already-sticky check_failed.
  // This removes the check_active -> check_ready chain from fault capture,
  // without moving the sampling edge or weakening any invalid-owner condition.
  else if(((check_enable || check_request) && (loader_run || !loaded || boot_fault)) ||
          (check_enable && (load_begin || load_valid || load_end || start)) ||
          (check_request && (!check_enable || !raw_check_ready || !address_valid)))check_failed<=1;
 wire [21:0] load_address,read_address;wire [15:0] load_pin_data;wire load_drive;
 wire load_1ce,load_2ce,load_oe,load_we,load_bhe,load_ble;
 wire read_1ce,read_2ce,read_oe,read_we,read_bhe,read_ble;
 nes_rom_loader loader(.rom_chr32(rom_chr32),.mem_clk(mem_clk),.reset(reset),.load_begin(load_begin && !check_failed),.load_chr32(load_chr32),.load_valid(load_valid && !check_failed),.load_end(load_end && !check_failed),.start(start && !check_failed),.stop(stop),.load_data(load_data),.load_ready(load_ready),.loaded(loaded),.run_enable(loader_run),.fault(boot_fault),.error_code(boot_error),.loaded_bytes(loaded_bytes),.load_address(load_address),.load_pin_data(load_pin_data),.load_drive(load_drive),.load_1ce(load_1ce),.load_2ce(load_2ce),.load_oe(load_oe),.load_we(load_we),.load_bhe(load_bhe),.load_ble(load_ble));
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem_clk),.reset(reader_reset),
 .check_mode(check_active),.check_request(check_request && raw_check_ready && address_valid && !check_failed),
 .check_address(physical_check_address),.check_ready(raw_check_ready),.check_response(raw_check_response),
 .check_response_address(raw_check_address),.check_data(check_data),
 .rom_request(rom_request && run_enable),.rom_address(rom_address),.rom_ready(rom_ready),.rom_response(rom_response),.rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .psram_address(read_address),.psram_1ce(read_1ce),.psram_2ce(read_2ce),.psram_oe(read_oe),.psram_we(read_we),.psram_bhe(read_bhe),.psram_ble(read_ble),.psram_data(psram_data));
 assign psram_address=reader_owner?read_address:load_address;
 assign psram_1ce=reset?1'b1:reader_owner?read_1ce:load_1ce;
 assign psram_2ce=reset?1'b1:reader_owner?read_2ce:load_2ce;
 assign psram_oe=reset?1'b1:reader_owner?read_oe:load_oe;
 assign psram_we=reset?1'b1:reader_owner?read_we:load_we;
 assign psram_bhe=reset?1'b1:reader_owner?read_bhe:load_bhe;
 assign psram_ble=reset?1'b1:reader_owner?read_ble:load_ble;
 assign psram_data=(!reset && !reader_owner && load_drive)?load_pin_data:16'hzzzz;
endmodule
