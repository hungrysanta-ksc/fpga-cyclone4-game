// Integrated release BEGIN / END / START endpoint with the actual loader.
`timescale 1ns/1ps
module nes_retail1054_tb #(parameter TOTAL=786432);
 logic clk=0,reset=1,ss=1,sck=0,mosi=0;
 always #3 clk=!clk;
 wire start,stop,go,mode,valid,last,run,loaded,ready,bad,fault,miso,we;
 wire [19:0] count;
 wire [3:0] code;
 nes_rom_spi_check dut(.mem_clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .spi_miso(miso),.load_ready(ready),.loaded(loaded),.loaded_bytes(count),.run_enable(run),
  .boot_fault(bad),.boot_error(code),.load_begin(go),.load_chr32(mode),.load_valid(valid),
  .load_end(last),.start(start),.stop(stop),.fault(fault),.check_ready(1'b1),
  .check_response(1'b0),.check_fault(1'b0),.check_response_address(20'd0),.check_data(8'd0));
 nes_rom_loader loader(.mem_clk(clk),.reset(reset),.load_begin(go),.load_chr32(mode),
  .load_valid(valid),.load_data(8'd0),.commands_blocked(fault),.load_end(last),.start(start),.stop(stop),
  .load_ready(ready),.loaded(loaded),.run_enable(run),.fault(bad),.error_code(code),
  .loaded_bytes(count),.load_we(we));
 always @(posedge clk) if(!reset && !we)$fatal(1,"unexpected PSRAM write");
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
 task clear;
  reset=1;#90;reset=0;#90;status(0);
 endtask
 initial begin
  clear();packet('h63,TOTAL,0);if(!fault||run)$fatal(1,"premature START");
  clear();packet('h60,0,3);status(0);if(count!==TOTAL)$fatal(1,"count %d",count);
  packet('h62,TOTAL,0);status('h82);
  packet('h63,TOTAL,0);status('h86);
  if(TOTAL==524288)begin
   packet('h64,TOTAL,1);status('h82);packet('h63,TOTAL,0);status('h86);
  end
  packet('h64,TOTAL,0);status(2);
  packet('h63,TOTAL,0);if(!fault||run)$fatal(1,"restart after stop");
  clear();packet('h60,0,3);packet('h62,TOTAL-1,0);
  if(!fault||run)$fatal(1,"wrong END offset");
  $display("PASS1054 adoption, count, reset, START and STOP %d",TOTAL);$finish;
 end
endmodule
