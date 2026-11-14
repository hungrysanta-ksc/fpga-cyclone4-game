// Physical SPI mode 0, asynchronous SNES write and 168 MHz loader comparator.
`timescale 1ns/1ps
module tb_nes_frame769;
 reg clk=0,mem_clk=0,reset=1,active=1,write_n=1,ss=1,sck=0,mosi=0;
 always #6 clk=~clk;
 always #3 mem_clk=~mem_clk;
 reg [23:0] addr=0; reg [7:0] data=0;
 wire wr,sel,miso;
 nes_screen_status151 screen(clk,reset,active,addr,1'b1,write_n,1'b1,data,1'b0,ss,sck,mosi,wr,sel,miso);
 `define INPUTS .mem_clk(mem_clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.load_ready(1'b1),.loaded(1'b0),.run_enable(1'b0),.boot_fault(1'b0),.boot_error(4'd0),.loaded_bytes(19'd0),.check_ready(1'b1),.check_response(1'b0),.check_fault(1'b0),.check_response_address(19'd0),.check_data(8'd0)
 nes_rom_spi_check loader(`INPUTS);
 original_spi_check reference(`INPUTS);
 always @(negedge mem_clk) if(!reset && (loader.sampled||loader.captured||loader.pending))
  if ({loader.pending_header_error,loader.pending_command,loader.pending,loader.error_code,loader.fault} !==
      {reference.pending_header_error,reference.pending_command,reference.pending,reference.error_code,reference.fault})
   $fatal(1,"loader header/retirement mismatch");
 task bus(input [23:0] a,input [7:0] v);
  addr=a;data=v;#99;write_n=0;#102;write_n=1;#102;
 endtask
 task octet(input [7:0] value,output [7:0] got);
  for(integer i=7;i>=0;i=i-1)begin mosi=value[i];#170;got[i]=miso;sck=1;#190;sck=0;#20;end
 endtask
 reg [63:0] answer; reg [7:0] b;
 task page(input [7:0] op,input bit mutate);
  ss=0;#205;octet(op,b);answer=0;
  for(integer k=1;k<8;k=k+1) begin
   if(mutate && k==3)bus('h7005,'h02);
   octet(0,b); answer={answer[55:0],b};
  end
  if(!sel)$fatal(1,"unselected status");
  ss=1;#500;
 endtask
 task header(input [7:0] op,arg,input integer damage);
  reg [63:0] tx;reg [7:0] crc;
  reset=1;#65;reset=0;#150;ss=0;#190;
  tx={op,24'd0,arg,(~arg)^(damage==1?8'd1:8'd0),16'h00a5};
  crc=0;
  for(integer k=63;k>=16;k=k-1) begin
   if(crc[7]^tx[k])crc=(crc<<1)^8'h07;else crc=crc<<1;
  end
  tx[15:8]=crc^(damage==2?8'd1:8'd0);
  if(damage==3)tx[0]=0;
  for(integer k=7;k>=(damage==4?1:0);k=k-1)octet(tx[k*8+:8],b);
  ss=1;#500;
  if(loader.pending_header_error!==reference.pending_header_error)$fatal(1,"loader mismatch");
  if(loader.pending_header_error !== (damage==4?1:damage!=0?2:
      op>8'h6a || (op!=8'h61 && op!=8'h68 && (op==8'h60 ? arg!=2:arg!=0))?3:0))$fatal(1,"unexpected header status %x %x %d %x",op,arg,damage,loader.pending_header_error);
 endtask
 initial begin
  #100;reset=0;#100;bus('h7000,'h7e);bus('h7001,'ha9);
  bus('h7004,'hfe);bus('h7005,'hff);bus('h7006,0);bus('h7007,1);
  page('h78,1);if(answer[55:0]!==56'h78feff00015aa5)$fatal(1,"snapshot %x",answer);
  bus('h017004,2);page('h78,0);if(answer[55:0]!==56'h78fe0200015aa5)$fatal(1,"alias/refresh");
  page('h73,0);if(answer[55:32]!==24'he67ea9)$fatal(1,"STOP/error status");
  for(integer c=0;c<16;c=c+1)
   for(integer i=0;i<5;i=i+1)
    for(integer j=0;j<5;j=j+1)header('h60+c,i==4?8'hff:i,j);
  $display("PASS769 snapshot STOP and 400 loader frames");$finish;
 end
endmodule
