// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb_nes_spi914;
 reg clk=0,reset=1,stop=0,ss=1,sck=0,mosi=0;
 always #5.95 clk=~clk;
 reg source_fault=0,chunk_ready=0,ended=0,retire_done=0;
 reg [31:0] token=32'hacedf783;
 reg [6:0] witness=7'h4e;reg [7:0] nes_first=8'hd2;
 wire [55:0] original,candidate;
 `define PORTS(q) .clk(clk),.reset(reset),.stop(stop),.enable(1'b1),.source_fault(source_fault), \
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.chunk_ready(chunk_ready),.chunk_kind(token[21]), \
  .chunk_length(token[11:0]),.chunk_slot(token[20:11]),.chunk_generation(token[31:16]),.chunk_token(token), \
  .plan_idle(1'b1),.plan_ready(1'b1),.end_generation(16'h3579),.end_sealed(ended),.retire_done(retire_done), \
  .host_first(witness),.nes_first(nes_first),.selected(q[0]),.miso(q[1]),.fault(q[2]),.plan_write(q[3]), \
  .plan_data(q[11:4]),.plan_seal(q[12]),.plan_length(q[22:13]),.plan_plans(q[27:23]),.plan_crc(q[43:28]), \
  .retire(q[44]),.first905(q[45]),.snap903(q[46])
 nes_plan_spi200_reference old_port(`PORTS(original));
 nes_plan_spi200 new_port(`PORTS(candidate));
 integer ticks=0,seals=0,retires=0;
 always @(negedge clk)begin
  ticks++;if(ticks>12&&original[46:0]!==candidate[46:0])$fatal(1,"SPI difference at %d",ticks);
  if(candidate[12])seals++;
  if(candidate[44])retires++;
 end
 reg [7:0] crc;
 task send(input [7:0] b);
  crc=crc^b;repeat(8)crc=crc[7]?(crc<<1)^7:crc<<1;
  for(int j=7;j>=0;j--)begin
   mosi=b[j];repeat(9)@(negedge clk);sck=1;repeat(9)@(negedge clk);sck=0;
  end
 endtask
 task begin_spi;ss=0;crc=0;repeat(5)@(negedge clk);endtask
 task end_spi;repeat(8)@(negedge clk);ss=1;repeat(16)@(negedge clk);endtask
 task status(input bit valid);
  chunk_ready=valid;begin_spi();send('he8);
  for(int j=1;j<20;j++)begin
   if(j==5)begin chunk_ready=~valid;token=~token;end
   if(j==13)begin witness=~witness;nes_first=~nes_first;end
   send(8'h55^j);
  end
  end_spi();
 endtask
 task batch(input integer length,input integer payload,input bit broken);
  begin_spi();send('he9);send(length);send(length>>8);send(1);
  for(int j=0;j<payload;j++)send((j+length)*19);
  send('h23);send('h57);send(crc^broken);send('ha5);end_spi();
 endtask
 task restart;stop=1;repeat(8)@(negedge clk);stop=0;repeat(8)@(negedge clk);endtask
 initial begin
  repeat(8)@(negedge clk);reset=0;repeat(8)@(negedge clk);
  batch(3,3,0);batch(512,512,0);
  if(seals!=2||candidate[2])$fatal(1,"E9");
  status(0);status(1);chunk_ready=0;ended=1;@(negedge clk);ended=0;
  begin_spi();send('hea);send('h79);send('h35);send(0);send(2);send(crc);send('ha5);end_spi();
  if(retires!=1||candidate[2])$fatal(1,"EA");
  restart();batch(32,32,1);
  if(!candidate[2]||seals!=2)$fatal(1,"CRC");
  status(0);status(1);
  restart();batch(1024,4,0);if(!candidate[2])$fatal(1,"overflow");
  restart();batch(6,5,0);if(!candidate[2])$fatal(1,"partial payload");
  restart();begin_spi();send('he9);send(8);stop=1;send(0);end_spi();restart();status(1);
  $display("PASS914 SPI cycle comparison %0d edges, E9=%0d EA=%0d",ticks,seals,retires);$finish;
 end
endmodule
