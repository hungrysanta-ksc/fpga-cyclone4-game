// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module nes_chr_snoop601_tb;
 reg clk=0,reset=1,stop=0,immutable=1,capture_open=0,query_owned=0;
 reg [31:0] content_epoch=1;
 reg sample=0,sample_obj=0,query=0,query_obj=0;
 reg [16:0] sample_address=0,query_address=0;
 reg [7:0] sample_data=0;
 wire sample_ready,query_ready,response,hit;
 wire [7:0] data;
 nes_chr_snoop601 dut(.*);
 always #5 clk=~clk;
 task tick; begin @(posedge clk); #1; end endtask
 task sweep; integer i; begin
  capture_open=1;query_owned=0;
  for(i=0;i<256;i=i+1)begin if(sample_ready)$fatal(1,"short scrub");tick;end
  if(!sample_ready)$fatal(1,"late scrub");
 end endtask
 task fill(input integer k,a,b);begin
  capture_open=1;query_owned=0;sample_obj=k;sample_address=a;sample_data=b;sample=1;#1;
  if(!sample_ready)$fatal(1,"lost PPU sample");tick;sample=0;tick;
 end endtask
 task check_byte(input integer k,a,want,b);begin
  query_owned=1;capture_open=0;query_obj=k;query_address=a;query=1;#1;
  if(!query_ready)$fatal(1,"query not ready");tick;
  if(!response||hit!==want[0]||(hit&&data!==b[7:0]))$fatal(1,"lookup");
  query=0;
 end endtask
 integer fd,op,k,a,b,e,frames=0,fills=0,reads=0,hits=0,n;
 initial begin
  tick;reset=0;sweep;
  fd=$fopen("stim.tsv","r");
  while(!$feof(fd))begin
   n=$fscanf(fd,"%d %d %h %h %d\n",op,k,a,b,e);
   if(n!=5)$fatal(1,"input");
   case(op)
    0:begin stop=1;tick;stop=0;sweep;frames=frames+1;end
    1:begin fill(k,a,b);fills=fills+1;end
    2:begin check_byte(k,a,e,b);reads=reads+1;hits=hits+e;end
    default:$fatal(1,"operation");
   endcase
  end
  $fclose(fd);
  // Two mapped banks alias the same set; adjacent untouched lanes must miss.
  fill(0,17'h1110,12);fill(0,17'h1911,43);
  check_byte(0,17'h1110,0,0);check_byte(0,17'h1910,0,0);check_byte(0,17'h1911,1,43);
  fill(1,17'h1110,96);check_byte(0,17'h1911,1,43);check_byte(1,17'h1110,1,96);
  stop=1;#1;if(response||hit)$fatal(1,"stale after STOP");tick;stop=0;sweep;
  check_byte(1,17'h1110,0,0);
  fill(0,16,123);check_byte(0,16,1,123);content_epoch=2;#1;
  if(response||hit)$fatal(1,"stale at epoch");tick;sweep;check_byte(0,16,0,0);
  capture_open=1;query_owned=0;sample_address=22;sample=1;tick;sample=0;immutable=0;
  tick;immutable=1;sweep;check_byte(0,22,0,0);
  $display("PASS601 frames=%0d fills=%0d queries=%0d hits=%0d",frames,fills,reads,hits);
  $finish;
 end
endmodule
