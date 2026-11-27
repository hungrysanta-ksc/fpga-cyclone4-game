// Drive the production endpoint through FINISH/START and both kinds of STOP.
`timescale 1ns/1ps
module ff3_slot_stop1046_tb;
 reg clk=0,reset=1,ss=1,sck=0,mosi=0,run=0,reply=0,boot_fault=0;
 always #3 clk=!clk;
 wire start,stop,request,enabled,fault;
 wire [19:0] address;
 wire miso;
 reg [19:0] returned;
 nes_rom_spi_check dut(.mem_clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .spi_miso(miso),.load_ready(1'b0),.loaded(1'b1),.loaded_bytes(20'd1),.run_enable(run),
  .boot_fault(boot_fault),.boot_error(4'd0),.start(start),.stop(stop),.fault(fault),
  .check_enable(enabled),.check_ready(1'b1),.check_response(reply),.check_fault(1'b0),
  .check_request(request),.check_address(address),.check_response_address(returned),.check_data(8'ha6));
 always @(posedge clk)begin
  reply<=request;
  if(request)returned<=address;
  if(reset || stop)run<=0;else if(start)run<=1;
 end
 byte rx[8];
 task packet(input byte op,input int offset,input byte arg);
  byte b[8],crc;
  b[0]=op;b[1]=offset>>16;b[2]=offset>>8;b[3]=offset;b[4]=arg;b[5]=~arg;crc=0;
  for(int j=0;j<6;j++)begin
   crc^=b[j];repeat(8)crc=crc[7]?(crc<<1)^8'h07:crc<<1;
  end
  b[6]=crc;b[7]='ha5;ss=0;#120;
  for(int j=0;j<8;j++)for(int i=7;i>=0;i--)begin
   mosi=b[j][i];#60;sck=1;#60;rx[j][i]=miso;sck=0;
  end
  #120;ss=1;#180;
 endtask
 task status(input byte flags);
  packet('h65,0,0);if(rx[2]!==flags || fault)$fatal(1,"flags %h expected %h",rx[2],flags);
 endtask
 task verified_run;
  packet('h66,0,0);packet('h67,0,0);packet('h6a,0,0);
  if(rx[3]!==8'ha6)$fatal(1,"readback");
  packet('h68,0,'ha6);packet('h69,1,0);status('h82);
  packet('h63,1,0);status('h86);
 endtask
 initial begin
  repeat(4)@(negedge clk);reset=0;
  packet('h64,1,1);status(2);
  verified_run();packet('h64,1,1);status('h82);
  packet('h63,1,0);status('h86);packet('h64,1,0);status(2);
  packet('h63,1,0);if(run || !fault)$fatal(1,"ordinary STOP allowed restart");
  reset=1;#60;reset=0;verified_run();boot_fault=1;packet('h64,1,1);boot_fault=0;status(2);
  verified_run();packet('h64,1,1);status('h82);packet('h60,0,2);status(2);
  reset=1;#60;reset=0;verified_run();packet('h64,1,2);
  if(!fault)$fatal(1,"invalid STOP accepted");
  $display("PASS cold validation, slot restart, ordinary STOP, reset, ROM fault, new image, bad argument");$finish;
 end
endmodule
