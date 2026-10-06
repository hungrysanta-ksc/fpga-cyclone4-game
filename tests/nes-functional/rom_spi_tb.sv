// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rom_spi_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=0;
 always #23.280423 clk=~clk;
 always #5.952381 mem_clk=~mem_clk;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire spi_miso,spi_selected,load_ready,loaded,run_enable,boot_fault,spi_fault;
 wire [3:0] boot_error,spi_error;wire [16:0] loaded_bytes;
 reg rom_request=0;reg [21:0] rom_address=0;wire rom_ready,rom_response,rom_error;
 wire [21:0] rom_response_address,psram_address;wire [7:0] rom_data;
 wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_spi_boot dut(.*);rom_boot_model memory(.*);
 integer checks=0,negative_cases=0,reads=0;
 reg [7:0] tx[0:8],rx[0:8];
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;begin c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic check(input bit v);begin checks++;if(!v)$fatal(1,"SPI check%0d count%0d proto%0d boot%0d",checks,loaded_bytes,spi_error,boot_error);end endtask
 task automatic fresh;
  SPI_SS=1;SPI_SCK=0;SPI_MOSI=0;rom_request=0;reset=1;#200;reset=0;#200;
  check(!loaded&&!run_enable&&!spi_fault&&!boot_fault);
 endtask
 task automatic frame(input [7:0] op,input [23:0] address,input [7:0] arg);
  reg [7:0] c;begin
   tx[0]=op;tx[1]=address[23:16];tx[2]=address[15:8];tx[3]=address[7:0];tx[4]=arg;tx[5]=~arg;
   c=0;for(integer j=0;j<6;j++)c=crc_byte(c,tx[j]);tx[6]=c;tx[7]=8'ha5;tx[8]=0;
  end
 endtask
 // Accelerated digital stress, intentionally not a250kHz electrical test.
 task automatic transfer(input integer bits);
  SPI_SCK=0;SPI_SS=0;#120;
  for(integer j=0;j<bits;j++)begin
   SPI_MOSI=tx[j/8][7-j%8];#60;SPI_SCK=1;#60;rx[j/8][7-j%8]=spi_miso;SPI_SCK=0;
  end
  #120;SPI_SS=1;#240;
 endtask
 task automatic command(input [7:0] op,input [23:0] address,input [7:0] arg);
  frame(op,address,arg);transfer(64);
 endtask
 task automatic protocol_failure(input [3:0] code);
  check(spi_fault&&spi_error==code&&!loaded&&!run_enable);negative_cases++;
  command(8'h65,0,0);check(rx[1]==8'h54&&rx[3]=={4'd0,code}&&rx[2][3]);
 endtask
 task automatic read_byte(input [21:0] address,input [7:0] value);
  @(negedge clk);while(!rom_ready)@(negedge clk);
  rom_address=address;rom_request=1;@(negedge clk);rom_request=0;
  while(!rom_response)@(negedge clk);
  check(rom_data===value&&!rom_error&&rom_response_address===address);reads++;
  @(negedge clk);
 endtask
 integer i,writes_before;reg [23:0] addr;
 initial begin
  fresh();command(8'h60,0,0);frame(8'h61,0,8'h12);transfer(63);protocol_failure(1);check(memory.writes==0);
  fresh();command(8'h60,0,0);frame(8'h61,0,8'h12);transfer(72);protocol_failure(1);
  fresh();command(8'h60,0,0);frame(8'h61,0,8'h12);tx[6]^=1;transfer(64);protocol_failure(2);
  fresh();command(8'h6f,0,0);protocol_failure(3);
  fresh();command(8'h61,0,8'h12);protocol_failure(4);
  fresh();command(8'h60,0,0);command(8'h61,1,8'h12);protocol_failure(5);
  fresh();command(8'h60,0,0);command(8'h61,0,8'h12);check(loaded_bytes==1);command(8'h61,0,8'h12);protocol_failure(5);
  fresh();command(8'h63,0,0);check(boot_fault&&boot_error==3);negative_cases++;
  fresh();command(8'h60,0,0);command(8'h62,0,0);check(boot_fault&&boot_error==2);negative_cases++;
  fresh();command(8'h60,0,2);protocol_failure(3);
  fresh();command(8'h60,0,0);frame(8'h61,0,8'h12);transfer(16);protocol_failure(1);
  fresh();command(8'h60,0,0);frame(8'h61,0,8'h12);tx[7]=0;transfer(64);protocol_failure(2);
  fresh();command(8'h60,0,0);frame(8'h61,0,8'h12);tx[5]^=1;transfer(64);protocol_failure(2);
  fresh();command(8'h60,0,0);command(8'h61,0,8'h12);command(8'h64,1,0);check(loaded_bytes==0&&!load_ready&&!loaded);
  // Complete image enters RAM solely through serial commands and real WE pins.
  fresh();writes_before=memory.writes;command(8'h60,0,0);
  for(i=0;i<81920;i++)begin command(8'h61,i,i[7:0]^i[15:8]^8'ha5);check(!spi_fault&&!boot_fault&&loaded_bytes==i+1);end
  check(!loaded&&!run_enable&&memory.writes-writes_before==81920);
  command(8'h62,81920,0);check(loaded&&!run_enable);
  command(8'h63,81920,0);check(loaded&&run_enable);
  for(i=0;i<81920;i++)begin addr=i<65536?i:24'h200000+i-65536;read_byte(addr[21:0],i[7:0]^i[15:8]^8'ha5);end
  command(8'h65,0,0);check(rx[1]==8'h54&&rx[2]==6&&{rx[4],rx[5],rx[6]}==81920);
  command(8'h64,81920,0);check(loaded&&!run_enable);
  command(8'h63,81920,0);check(run_enable);read_byte(22'h200000,8'ha5);
  command(8'h61,81920,0);protocol_failure(4);check(psram_we&&psram_oe);
  fresh();command(8'h60,0,0);frame(8'h61,0,8'h88);
  fork transfer(64);begin #300;reset=1;#200;reset=0;end join
  check(memory.writes-writes_before==81920&&!loaded&&!run_enable);
  $display("PASS SPI BOOT checks=%0d reads=%0d negative_cases=%0d pin_bytes=81920",checks,reads,negative_cases);$finish;
 end
 initial begin #1200000000;$fatal(1,"SPI timeout");end
endmodule
