// Drain the board's actual map compressor and byte serializer over SPI.
`timescale 1ns/1ps
module kirby1023_ingress_tb;
 reg clk=0,reset=1,valid=0;
 always #6 clk=~clk;
 `include "spi200_bus.svh"
 wire ready,fault;
 reg [95:0] record_word;
 nes_native_spi165 dut(.clk(clk),.reset(reset),.SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),
 .selected(selected197),.miso(miso197),.record_valid(valid),.record_ready(ready),.record_data(record_word),
 .ack_ready(1'b1),.fault(fault));
 task cmd(input [7:0] op,input integer seq);
  reg [7:0] b[0:7]; integer j;
  begin b[0]=op;b[1]=0;b[2]=seq>>8;b[3]=seq;b[4]=0;b[5]=255;b[6]=0;b[7]=165;
   for(j=0;j<6;j++)b[6]=crc8_197(b[6],b[j]);
   begin197();for(j=0;j<8;j++)byte197(b[j],rx197[j]);end197();
  end
 endtask
 integer f,inf,outf,seq,n,j;reg [7:0] v;
 initial begin
  if(!$value$plusargs("FRAME=%d",f))$fatal;
  inf=$fopen($sformatf("frame%0d.wire",f),"r");outf=$fopen($sformatf("frame%0d.d1",f),"w");
  if(!inf||!outf)$fatal;
  repeat(4)@(negedge clk);reset=0;
  while($fscanf(inf,"%h",record_word)==1)begin
   @(negedge clk);while(!ready)@(negedge clk);
   valid=1;@(negedge clk);valid=0;
  end
 end
 initial begin
  seq=0;wait(!reset);
  forever begin
   wait(dut.available);cmd('hd0,0);
   n={rx197[5],rx197[6]};
   if(!rx197[2][0]||{rx197[3],rx197[4]}!=seq||!n||n>256)$fatal;
   begin197();byte197('hd1,v);for(j=0;j<n+2;j++)begin byte197(0,v);$fwrite(outf,"%02h",v);end
   end197();$fwrite(outf,"\n");cmd('hd2,seq);seq++;
   if(fault)$fatal;
   if(!valid && $feof(inf) && !dut.sealed && !dut.encoding)begin
    $fclose(outf);$display("PASS1023 ingress frame=%d blocks=%d",f,seq);$finish;
   end
  end
 end
 initial begin #80000000;$fatal(1,"timeout %0d",seq);end
endmodule
