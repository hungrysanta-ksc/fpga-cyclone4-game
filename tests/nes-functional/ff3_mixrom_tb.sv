`timescale 1ns/1ps
module ff3_mixrom_tb;
 reg clk=0;always #5 clk=!clk;
 reg [3:0] square1,square2,triangle,noise;reg [6:0] dmc;
 wire [15:0] expected,actual;
 APUMixer_reference original(.sample(expected),.*);
 APUMixer changed(.sample(actual),.*);
 initial begin
   for(int i=0;i<32768;i++)begin
     @(posedge clk); #1;
     {triangle,noise,dmc}=i[14:0];
     square1=i[3:0];square2=i[7:4];
     @(negedge clk);#1;
     if(expected!==actual || $isunknown(actual))$fatal(1,"mix mismatch %h %h %h",i,expected,actual);
   end
   $display("PASS FF3 mixer all 32768 triangle/noise/DMC combinations at DAC sample");
   $finish;
 end
endmodule
