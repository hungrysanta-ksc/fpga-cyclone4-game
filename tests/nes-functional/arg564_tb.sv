// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module arg564_tb;
 reg mem_clk=0,reset=1,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 always #2976 mem_clk=!mem_clk;
 reg load_ready=1,loaded=0,run_enable=0,boot_fault=0,check_ready=1,check_response=0,check_fault=0;
 reg [18:0] loaded_bytes=0,check_response_address=0;
 reg [3:0] boot_error=0;reg [7:0] check_data=0;
 wire [41:0] old_bus,new_bus;
`define PORTS(b) .spi_miso(b[41]),.spi_selected(b[40]),.load_begin(b[39]),.load_chr32(b[38]),.load_valid(b[37]),.load_end(b[36]),.start(b[35]),.stop(b[34]),.load_data(b[33:26]),.fault(b[25]),.error_code(b[24:21]),.check_enable(b[20]),.check_request(b[19]),.check_address(b[18:0]),.*
 ref_spi563 old_dut(`PORTS(old_bus));
 nes_rom_spi_check dut(`PORTS(new_bus));
 integer writes=0,checks=0,truncations=0,armed_aborts=0,starts=0,stops=0,read_requests=0;
 reg [7:0] written,expected_arg=0;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)expected_arg<=0;
  else if(!dut.ss_sync[1]&&dut.sck_sync[1]&&!dut.sck_previous&&dut.bit_count==7&&dut.byte_count==4)
   expected_arg<={dut.shift[6:0],dut.mosi_sync[1]};
  if(!reset && new_bus[37])begin writes++;written=new_bus[33:26];end
  if(!reset && new_bus[35])starts++;
  if(!reset && new_bus[34])stops++;
  if(!reset && new_bus[19])read_requests++;
 end
 always @(negedge mem_clk)begin
  checks++;
  if(old_bus!==new_bus||dut.arg!==old_dut.arg||dut.arg!==expected_arg)
   $fatal(1,"cycle %0t buses %h/%h args %h/%h expected %h reset %b",$time,old_bus,new_bus,old_dut.arg,dut.arg,expected_arg,reset);
  if(!reset&&!dut.ss_sync[1]&&dut.sck_sync[1]&&!dut.sck_previous&&dut.byte_last)
    if(dut.arg_write!==(dut.byte_count==4))$fatal(1,"argument enable");
 end
 reg [7:0] packet[0:9];
 function automatic [7:0] crc8(input [7:0] c,v);
  reg [7:0] x;begin x=c^v;repeat(8)x=x[7]?((x<<1)^7):x<<1;return x;end
 endfunction
 task build(input [7:0] cmd,value,input [23:0] address=0);
  reg [7:0] crc;packet[0]=cmd;packet[1]=address[23:16];packet[2]=address[15:8];packet[3]=address[7:0];
  packet[4]=value;packet[5]=~value;crc=0;for(int j=0;j<6;j++)crc=crc8(crc,packet[j]);
  packet[6]=crc;packet[7]='ha5;packet[8]='hff;packet[9]=0;
 endtask
 task bits(input integer count);
  SPI_SS=0;#115000;
  for(int n=0;n<count;n++)begin
   SPI_MOSI=packet[n/8][7-n%8];#95238;SPI_SCK=1;#190476;
   if(new_bus!==old_bus)$fatal(1,"pins");SPI_SCK=0;#95238;
  end
 endtask
 task read_check;
  restart();loaded=1;loaded_bytes=1;load_ready=0;
  build('h66,0);bits(64);finish_frame();
  build('h67,0);bits(64);finish_frame();
  if(!new_bus[20]||new_bus[25]||!dut.check_busy)$fatal(1,"CHECK read");
  @(negedge mem_clk);check_data='h9a;check_response=1;@(negedge mem_clk);check_response=0;
  repeat(8)@(negedge mem_clk);
  if(!dut.check_done||dut.checked_data!==8'h9a)$fatal(1,"CHECK response");
 endtask
 task finish_frame;
  SPI_SS=1;#2100000;
  if(dut.arg_write!==0)$fatal(1,"stale arg_write after SS");
 endtask
 task restart;
  reset=1;SPI_SS=1;SPI_SCK=0;#115000;reset=0;#120000;
 endtask
 task valid(input [7:0] value);
  integer before_n;before_n=writes;
  build('h61,value);bits(64);finish_frame();
  if(writes!=before_n+1||written!==value||new_bus[25])$fatal(1,"DATA %h code %h",value,new_bus[24:21]);
 endtask
 task reject(input integer n,input integer code);
  integer before_n;before_n=writes;bits(n);finish_frame();
  if(writes!=before_n||!new_bus[25]||new_bus[24:21]!=code)$fatal(1,"reject %0d code %0d",n,new_bus[24:21]);
 endtask
 initial begin
  if($test$plusargs("SHIFT"))#3100;restart();
  for(int i=0;i<256;i++)valid(i);
  for(int n=8;n<64;n++)begin restart();build('h61,'ha6);reject(n,1);truncations++;end
  restart();build('h61,9);reject(80,1);
  for(int k=0;k<3;k++)begin restart();build('h61,'ha6);packet[5+k]^=1;reject(64,2);end
  restart();build('h6f,0);reject(64,3);
  // Abort a foreign command at every bit of the argument; the next legal
  // packet follows without resetting the receiver or its argument register.
  for(int n=32;n<=40;n++)begin
   restart();build('h11,'haa);bits(n);
   if(n==39)begin if(!dut.arg_write)$fatal(1,"unguarded abort");armed_aborts++;end
   finish_frame();valid(8'hff-n);
  end
  // Reset between bit seven and eight without a closing SS edge.
  build('h61,'h3c);bits(39);if(!dut.arg_write)$fatal(1,"missing arm");
  reset=1;#1000;if(dut.arg_write||dut.arg!==0)$fatal(1,"reset");restart();valid('hc3);
  read_check();build('h68,'h9b);reject(64,8);
  read_check();build('h68,'h9a);bits(64);finish_frame();
  if(dut.check_next!=1||new_bus[25])$fatal(1,"checked ACK");
  build('h69,0,1);bits(64);finish_frame();
  build('h63,0,1);bits(64);finish_frame();run_enable=1;
  build('h64,0,1);bits(64);finish_frame();
  if(new_bus[25]||starts!=1||stops!=1||read_requests!=2||dut.verified)$fatal(1,"START/STOP");
  $display("PASS564 writes=%0d trunc=%0d armed=%0d checks=%0d",writes,truncations,armed_aborts,checks);
  $finish;
 end
 initial begin #(64'd30000000000);$fatal(1,"timeout");end
endmodule
