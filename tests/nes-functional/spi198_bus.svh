// Mode0 8MHz, asynchronous to84MHz host. Two-us SS-high gap matches MCU.
reg ss197=1,sck197=0,mosi197=0;wire selected197,miso197;
parameter real SPI_HALF=62.5,SPI_SETUP=200,SPI_HOLD=200,SPI_GAP=2000;
reg [7:0] rx197[0:63];integer spi_calls197=0;
function automatic [7:0] crc8_197(input [7:0] c0,input [7:0] b);
 reg [7:0] c;integer k;begin c=c0^b;for(k=0;k<8;k=k+1)c=c[7]?(c<<1)^8'h07:c<<1;crc8_197=c;end
endfunction
task byte197(input [7:0] b,output [7:0] r);
 integer k;begin r=0;for(k=7;k>=0;k=k-1)begin
  mosi197=b[k];#(SPI_HALF);sck197=1;r[k]=miso197;#(SPI_HALF);sck197=0;
 end end
endtask
task begin197;begin ss197=0;#(SPI_SETUP);end endtask
task end197;begin #(SPI_HOLD);ss197=1;#(SPI_GAP);spi_calls197++;end endtask
task status197;
 integer k;reg [7:0] c;begin
  begin197();byte197(8'he8,rx197[0]);for(k=1;k<20;k=k+1)byte197(0,rx197[k]);end197();
  c=0;for(k=1;k<19;k=k+1)c=crc8_197(c,rx197[k]);
  if(rx197[1]!=8'hd7||rx197[2]!=2||rx197[18]!=0||rx197[19]!=c)$fatal(1,"status CRC/version");
 end
endtask
