// SPDX-License-Identifier: MIT
// DPI prefix experiment: actual loader/FatFS and SPI+boot RTL; deliberately
// abort after TEST_LIMIT DATA requests. This is not the complete loading path.
`timescale 1ns/1ps
module prefix_tb;
 reg clk=0,mem_clk=0,reset=1;
 always #23.280423 clk=~clk;
 always #2.9761905 mem_clk=~mem_clk;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire load_begin,load_chr32,load_valid,load_end,start,stop;
 wire [7:0] load_data,check_data;
 wire load_ready,loaded,run_enable,boot_fault,check_enable,check_request,check_ready,check_response,check_fault;
 wire [3:0] boot_error;wire [18:0] loaded_bytes,check_address,check_response_address;
 wire fault;wire [3:0] error_code;wire spi_miso;
 nes_rom_spi_check dut(.*,.spi_selected());
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;
 wire [15:0] psram_data;
 reg [15:0] chip0[0:1048575],chip1[0:1048575];
 assign psram_data=!psram_oe && !psram_1ce ? chip0[psram_address[19:0]] :
                   !psram_oe && !psram_2ce ? chip1[psram_address[19:0]] : 16'hzzzz;
 always @(negedge psram_we) begin
  if(!psram_1ce)begin
   if(!psram_bhe)chip0[psram_address[19:0]][15:8]=psram_data[15:8];
   if(!psram_ble)chip0[psram_address[19:0]][7:0]=psram_data[7:0];
  end
  if(!psram_2ce)begin
   if(!psram_bhe)chip1[psram_address[19:0]][15:8]=psram_data[15:8];
   if(!psram_ble)chip1[psram_address[19:0]][7:0]=psram_data[7:0];
  end
 end
 nes_rom_boot boot(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(1'b1),
 .check_enable(check_enable),.check_request(check_request),.check_address(check_address),.check_ready(check_ready),
 .check_response(check_response),.check_response_address(check_response_address),.check_data(check_data),.check_fault(check_fault),
 .load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),
 .load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),
 .rom_chr32(),.rom_request(1'b0),.rom_address(22'd0),.rom_ready(),.rom_response(),.rom_error(),.rom_response_address(),.rom_data(),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),
 .psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 task spi_transfer(input longint unsigned tx,output longint unsigned rx);
  #2000;SPI_SS=0;#2000;rx=0;
  for(integer j=0;j<64;j++)begin
   SPI_MOSI=tx[63-j];#190.476;SPI_SCK=1;#190.476;
   rx={rx[62:0],spi_miso};SPI_SCK=0;
  end
  #2000;SPI_SS=1;
 endtask
 import "DPI-C" function void start_worker();
 import "DPI-C" function int next_request(output longint unsigned tx);
 import "DPI-C" function void submit_response(input longint unsigned rx);
 import "DPI-C" function int worker_result();
 initial begin
  longint unsigned tx,rx;integer pending;
  #1000;reset=0;#1000;start_worker();
  pending=next_request(tx);
  while(pending==1)begin spi_transfer(tx,rx);submit_response(rx);pending=next_request(tx);end
  if(pending!=0)$fatal(1,"DPI worker request timeout");
  if(worker_result()!=0)$fatal(1,"loader fixture failed");
  if(loaded_bytes!==`TEST_LIMIT || loaded || run_enable || fault)$fatal(1,"unexpected prefix state count=%d fault=%d",loaded_bytes,fault);
  for(integer i=0;i<`TEST_LIMIT;i++)begin
   reg [15:0] word_data;reg [7:0] actual;
   word_data=i[1] ? chip1[i>>2] : chip0[i>>2];
   actual=i[0] ? word_data[7:0] : word_data[15:8];
   if(actual!==8'((i+16)^((i+16)>>8)^8'ha5))$fatal(1,"PSRAM prefix mismatch %0d %h",i,actual);
  end
  $display("PASS NROM410 real C/FatFS to real RTL prefix bytes=%0d",loaded_bytes);
  $finish;
 end
endmodule
