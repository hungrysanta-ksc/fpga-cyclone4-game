// SPDX-License-Identifier: MIT
// Decoder/mailbox test with an independent memory-clock response model.
`timescale 1ns/1ps
module spi_readback_control_tb;
 reg mem_clk=0,reset=1,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 always #5.952381 mem_clk=~mem_clk;
 wire spi_miso,spi_selected,load_begin,load_chr32,load_valid,load_end,start,stop,fault;
 wire [7:0] load_data;wire [3:0] error_code;
 reg load_ready=0,loaded=1,run_enable=0,boot_fault=0;reg [3:0] boot_error=0;reg [16:0] loaded_bytes=16;
 wire check_enable,check_request;wire [16:0] check_address;
 reg check_ready=1,check_response=0,check_fault=0;reg [16:0] check_response_address=0;reg [7:0] check_data=0;
 reg suppress=0,bad_tag=0;integer delay_count=0;reg [16:0] accepted;
 nes_rom_spi_check dut(.*);
 always @(posedge mem_clk)begin
  check_response<=0;
  if(reset)begin delay_count<=0;run_enable<=0;end
  else begin
   if(start)run_enable<=1;
   // Match053 STOP: RUN returns to loaded READY; pre-RUN STOP discards length.
   if(stop)begin
    run_enable<=0;
    if(!run_enable)begin loaded<=0;loaded_bytes<=0;end
   end
   if(check_request)begin accepted<=check_address;delay_count<=4;end
   else if(delay_count>0)begin
    delay_count<=delay_count-1;
    if(delay_count==1&&!suppress)begin check_response<=1;check_response_address<=accepted+(bad_tag?1:0);check_data<=accepted[7:0]^8'ha5;end
   end
  end
 end
 reg [7:0] tx[8],rx[8];integer checks=0,negatives=0;
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;begin c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic ck(input bit ok,input string why);
  checks++;if(!ok)$fatal(1,"CHECK CONTROL %0d %s error%0d flags%h",checks,why,error_code,rx[2]);
 endtask
 task automatic frame(input [7:0] op,input [23:0] address,input [7:0] arg);
  reg [7:0] c;
  tx[0]=op;tx[1]=address[23:16];tx[2]=address[15:8];tx[3]=address[7:0];tx[4]=arg;tx[5]=~arg;c=0;
  for(integer j=0;j<6;j++)c=crc_byte(c,tx[j]);tx[6]=c;tx[7]=8'ha5;
 endtask
 task automatic transfer(input integer bits);
  SPI_SCK=0;SPI_SS=0;#120;
  for(integer j=0;j<bits;j++)begin
   SPI_MOSI=tx[j/8][7-j%8];#60;SPI_SCK=1;#60;rx[j/8][7-j%8]=spi_miso;SPI_SCK=0;
  end
  #120;SPI_SS=1;#240;
 endtask
 task automatic command(input [7:0] op,input [23:0] a,input [7:0] arg);
  frame(op,a,arg);transfer(64);
 endtask
 task automatic fresh;
  reset=1;SPI_SS=1;SPI_SCK=0;suppress=0;bad_tag=0;check_fault=0;boot_fault=0;check_ready=1;
  loaded=1;loaded_bytes=16;#200;reset=0;#200;
 endtask
 task automatic open_check;
  command(8'h66,0,0);ck(check_enable&&!fault,"open");
 endtask
 task automatic expect_fault(input [3:0] code);
  ck(fault&&error_code==code&&!check_enable&&!start,"expected fault");negatives++;
 endtask
 initial begin
  fresh();command(8'h6b,0,0);expect_fault(3);
  fresh();command(8'h61,16,0);expect_fault(4);
  fresh();command(8'h60,1,0);expect_fault(5);
  fresh();command(8'h63,16,0);expect_fault(8);
  fresh();open_check();command(8'h69,16,0);expect_fault(8);
  fresh();open_check();command(8'h67,1,0);expect_fault(6);
  fresh();open_check();command(8'h68,0,8'ha5);expect_fault(8);
  fresh();open_check();command(8'h67,0,0);command(8'h68,0,0);expect_fault(8);
  fresh();open_check();command(8'h67,0,0);command(8'h68,0,8'ha5);command(8'h68,0,8'ha5);expect_fault(8);
  fresh();open_check();command(8'h67,0,0);command(8'h67,0,0);expect_fault(6);
  fresh();open_check();suppress=1;command(8'h67,0,0);command(8'h67,0,0);expect_fault(6);
  fresh();open_check();bad_tag=1;command(8'h67,0,0);expect_fault(7);
  fresh();open_check();frame(8'h67,0,0);tx[6]^=1;transfer(64);expect_fault(2);
  fresh();open_check();frame(8'h67,0,0);transfer(63);expect_fault(1);
  fresh();open_check();command(8'h60,0,0);expect_fault(6);
  fresh();open_check();command(8'h61,16,0);expect_fault(6);
  fresh();open_check();check_fault=1;#100;expect_fault(9);
  fresh();loaded=0;command(8'h66,0,0);expect_fault(6);
  fresh();open_check();suppress=1;command(8'h67,0,0);command(8'h64,16,0);
  ck(!check_enable&&!fault&&!run_enable&&!loaded,"STOP cancels busy");
  fresh();open_check();
  for(integer a=0;a<16;a++)begin
   command(8'h67,a,0);
   for(integer repeat_query=0;repeat_query<3;repeat_query++)begin
    // Deliberately overwrite decoder offset with unrelated STATUS arguments.
    command(8'h6a,24'hfedcba,0);
    ck(rx[1]==8'h59&&rx[2]==8'h62&&rx[3]==(a^8'ha5)&&{rx[4],rx[5],rx[6]}==a&&rx[7]==0,"held data/tag");
    command(8'h65,24'h123456,0);ck(rx[2]==8'h62&&{rx[4],rx[5],rx[6]}==16,"query has no ack");
   end
   command(8'h68,a,a^8'ha5);ck(!fault,"ACK");
  end
  command(8'h69,16,0);command(8'h65,0,0);ck(rx[2]==8'h82&&!check_enable,"all ACKs enable RUN");
  command(8'h63,16,0);command(8'h65,0,0);ck(rx[2]==8'h86&&run_enable,"verified START");
  command(8'h64,16,0);command(8'h65,0,0);ck(rx[2]==2,"RUN STOP preserves loaded but revokes verification");
  $display("PASS SPI CHECK CONTROL checks=%0d negative_cases=%0d ordered_acks=16 repeated_queries=96",checks,negatives);$finish;
 end
 initial begin #10000000;$fatal(1,"control watchdog");end
endmodule
