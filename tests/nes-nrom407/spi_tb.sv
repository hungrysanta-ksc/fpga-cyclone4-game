`timescale 1ns/1ps
module spi_tb;
 reg mem_clk=0,reset=1,ss=1,sck=0,mosi=0;
 always #3 mem_clk=~mem_clk;
 wire miso,selected,stop,fault;wire [3:0] error_code;
 reg saw_stop=0;
 nes_rom_spi_check dut(.mem_clk(mem_clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .spi_miso(miso),.spi_selected(selected),.load_ready(1'b0),.loaded(1'b0),.run_enable(1'b0),
  .boot_fault(1'b0),.boot_error(4'd0),.loaded_bytes(19'd0),.load_begin(),.load_chr32(),
  .load_valid(),.load_end(),.start(),.stop(stop),.load_data(),.fault(fault),.error_code(error_code),
  .check_enable(),.check_request(),.check_address(),.check_ready(1'b0),.check_response(1'b0),
  .check_fault(1'b0),.check_response_address(19'd0),.check_data(8'd0));
 always @(posedge mem_clk)if(stop)saw_stop<=1;
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;return c;
 endfunction
 task frame(input [7:0] op, output [63:0] received);
  reg [7:0] tx[0:7];reg [7:0] c;
  tx[0]=op;tx[1]=0;tx[2]=0;tx[3]=0;tx[4]=0;tx[5]=8'hff;
  c=0;for(integer k=0;k<6;k++)c=crc_byte(c,tx[k]);tx[6]=c;tx[7]=8'ha5;
  received=0;ss=0;#2000;
  for(integer j=0;j<64;j++)begin
   mosi=tx[j/8][7-j%8];#190.476;sck=1;#100;received={received[62:0],miso};#90.476;sck=0;
  end
  #2000;ss=1;#2000;
 endtask
 reg [63:0] answer;
 initial begin
  #100;reset=0;#1000;
  frame(8'h65,answer);
  if(answer[55:48]!==8'h78 || fault)$fatal(1,"status ID expected78 got %h fault%b",answer[55:48],fault);
  frame(8'h64,answer);
  if(!saw_stop || fault)$fatal(1,"actual STOP command lost fault%b code%h",fault,error_code);
  frame(8'h65,answer);
  if(answer[55:48]!==8'h78 || fault)$fatal(1,"status after STOP");
  $display("NROM407 SPI PASS serial status78 and STOP");$finish;
 end
 initial begin #200000;$fatal(1,"SPI407 timeout");end
endmodule
