// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rom_boot_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=0;
 always #23.280423 clk=~clk;
 initial begin #3.5;forever #5.952381 mem_clk=~mem_clk;end
 reg load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;reg [7:0] load_data=0;
 wire load_ready,loaded,run_enable,boot_fault;wire [3:0] boot_error;wire [16:0] loaded_bytes;
 reg rom_request=0;reg [21:0] rom_address=0;wire rom_ready,rom_response,rom_error;wire [21:0] rom_response_address;wire [7:0] rom_data;
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_boot dut(.*);rom_boot_model memory(.*);
 integer checks=0,read_count=0,negative_cases=0;
 function automatic [7:0] expected(input [21:0] a,input bit mode);expected=a[7:0]^a[15:8]^{a[19:16],2'b0,a[21:20]}^(mode?8'h3c:8'ha5);endfunction
 task automatic check(input bit v);if(!v)$fatal(1,"BOOT check%0d count%0d code%0d",checks,loaded_bytes,boot_error);checks++;endtask
 task automatic reset_all;
  #1.111;reset=1;load_begin=0;load_valid=0;load_end=0;start=0;stop=0;rom_request=0;
  #1;check(psram_we && psram_oe && psram_1ce && psram_2ce && !run_enable);
  repeat(3)@(negedge mem_clk);reset=0;repeat(3)@(negedge mem_clk);check(!loaded && !boot_fault && !rom_ready);
 endtask
 task automatic begin_load(input bit mode);
  @(negedge mem_clk);load_chr32=mode;load_begin=1;@(negedge mem_clk);load_begin=0;check(load_ready && !run_enable);
 endtask
 task automatic send_byte(input [7:0] v);
  while(!load_ready)@(negedge mem_clk);
  load_data=v;load_valid=1;@(negedge mem_clk);load_valid=0;
 endtask
 task automatic command_start;
  @(negedge mem_clk);start=1;@(negedge mem_clk);start=0;
 endtask
 task automatic read_byte(input [21:0] address,input bit mode);
  @(negedge clk);while(!rom_ready)@(negedge clk);
  rom_address=address;rom_request=1;@(negedge clk);rom_request=0;rom_address=~address;
  while(!rom_response)@(negedge clk);
  check(rom_response_address===address && rom_data===expected(address,mode) && !rom_error);read_count++;
  @(negedge clk);check(!rom_response);
 endtask
 task automatic failed(input [3:0] code);
  @(negedge mem_clk);while(!psram_1ce || !psram_2ce)@(negedge mem_clk);check(boot_fault && boot_error==code && !loaded && !run_enable && psram_we && psram_oe && !load_ready);negative_cases++;
  repeat(3)@(negedge mem_clk);check(boot_fault && boot_error==code);
 endtask
 always @(negedge mem_clk)if(!reset)begin
  if(run_enable)begin if(!psram_we)$fatal(1,"write while running");end
  if(!psram_oe && dut.load_drive)$fatal(1,"read/write ownership conflict");
 end
 initial begin
  reset_all();command_start();failed(3);
  reset_all();begin_load(0);load_begin=1;@(negedge mem_clk);load_begin=0;failed(1);
  reset_all();begin_load(0);load_end=1;@(negedge mem_clk);load_end=0;failed(2);
  reset_all();load_valid=1;@(negedge mem_clk);load_valid=0;failed(4);
  reset_all();load_begin=1;start=1;@(negedge mem_clk);load_begin=0;start=0;failed(5);
  reset_all();begin_load(0);send_byte(8'h77);reset_all();check(!loaded && loaded_bytes==0);
  begin_load(0);send_byte(8'h91);load_end=1;@(negedge mem_clk);load_end=0;failed(2);
  reset_all();begin_load(0);send_byte(8'h92);stop=1;@(negedge mem_clk);stop=0;failed(6);reset_all();
  for(integer mode=0;mode<2;mode++)begin
   integer length,before_writes;reg [21:0] address;
   begin_load(mode!=0);length=65536+(mode?32768:16384);before_writes=memory.writes;
   for(integer i=0;i<length;i++)begin
    address=i<65536?i:22'h200000+(i-65536);send_byte(expected(address,mode!=0));
   end
   while(loaded_bytes!=length)@(negedge mem_clk);
   check(!loaded && !load_ready && !run_enable && memory.writes-before_writes==length);
   load_end=1;@(negedge mem_clk);load_end=0;check(loaded && !run_enable);
   command_start();check(run_enable);
   for(integer i=0;i<length;i++)begin address=i<65536?i:22'h200000+(i-65536);read_byte(address,mode!=0);end
   // Stop cancels an in-flight read, leaving a valid immutable image to restart.
   @(negedge clk);rom_address=22'h3210;rom_request=1;@(negedge clk);rom_request=0;
   @(negedge mem_clk);stop=1;@(negedge mem_clk);stop=0;check(!run_enable && loaded && !rom_response);
   repeat(6)@(negedge clk);check(!rom_response);command_start();read_byte(22'h3210,mode!=0);
   if(mode==0)begin @(negedge mem_clk);stop=1;@(negedge mem_clk);stop=0;end
  end
  @(negedge mem_clk);load_valid=1;@(negedge mem_clk);load_valid=0;failed(4);
  check(read_count==180226);
  $display("PASS BOOT checks=%0d read_bytes=%0d negative_cases=%0d images=2",checks,read_count,negative_cases);$finish;
 end
 initial begin #200000000;$fatal(1,"watchdog");end
endmodule
