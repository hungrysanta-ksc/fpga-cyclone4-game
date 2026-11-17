// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module map829_tb;
 reg clk=0,reset=1,active=1,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;
 reg rn=1,wn=1,romsel=1;
 reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault,sreset;
 wire [7:0] dout;
 wire [15:0] pads;
 nes_sink_bridge165 dut(.clk(clk),.raw_reset(reset),.active(active),.stop(stop),.session_release_reset(sreset),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.spi_selected(selected),.spi_miso(miso),
  .address(address),.read_n(rn),.write_n(wn),.romsel_n(romsel),.data_in(din),
  .data_out(dout),.oe_n(oe),.dir(dir),.pad_commit(pc),.pad_buttons(pads),.fault(fault));
 always #5.952 clk=~clk;
 reg [7:0] wire_packet[0:255],ack[0:11],view_data[0:255],status[0:19];
 integer stream,lut,n,count,off,val,scan,cases,expanded,k;
 string input_path,output_path;
 function automatic [15:0] crc16(input [15:0] init,input [7:0] b);
  reg [15:0] c;
  c=init^{b,8'b0};repeat(8)c=c[15]?(c<<1)^16'h1021:c<<1;
  return c;
 endfunction
 task spi(input [7:0] b,output reg [7:0] r);
  for(int i=7;i>=0;i--)begin
   mosi=b[i];#190.476;sck=1;r[i]=selected?miso:0;#190.476;sck=0;
  end
 endtask
 task push(input bit bad_crc);
  reg [15:0] crc;
  reg [7:0] rx;
  crc=crc16('hffff,'he1);ss=0;#100;spi('he1,rx);
  for(int i=0;i<n;i++)begin spi(wire_packet[i],rx);crc=crc16(crc,wire_packet[i]);end
  spi(crc[15:8],rx);spi(crc[7:0]^bad_crc,rx);#100;ss=1;#150;
 endtask
 task bus_read(input [23:0] a,output reg [7:0] value);
  address=a;#35;rn=0;#83;
  if(oe || !dir)$fatal(1,"undriven read %h",a);
  value=dout;rn=1;#65;
 endtask
 task bus_write(input [23:0] a,input [7:0] v);
  address=a;din=v;#32;wn=0;#85;wn=1;#80;
 endtask
 task publish;
  for(int i=0;i<12;i++)bus_write('h6010+i,ack[i]);
  bus_write('h601c,'ha5);#400;
 endtask
 task restart;
  reset=1;stop=0;#160;reset=0;#300;
 endtask
 task logical_ready;
  reg [7:0] v;
  bus_read('h6000,v);if(v!=1)$fatal(1,"no head");
  bus_read('h6004,v);if(v!=expanded)$fatal(1,"bad logical length");
  bus_read('h6005,v);if(v!=0)$fatal(1,"bad length high");
 endtask
 task expect_fault;
  if(!fault || dut.endpoint.retired!=0)$fatal(1,"bad receipt escaped");
 endtask
 task negatives;
  reg [7:0] v;
  reg [7:0] saved[0:255];integer previous_n;
  restart();push(1);expect_fault();
  restart();wire_packet[12]-=1;push(0);expect_fault();wire_packet[12]+=1;
  restart();wire_packet[10]^=1;push(0);expect_fault();wire_packet[10]^=1;
  // STOP during the second literal. Uncommitted slot bytes survive in M9K,
  // but neither its identity nor its read coverage may survive recovery.
  restart();ss=0;#100;spi('he1,v);
  for(int i=0;i<18;i++)spi(wire_packet[i],v);
  stop=1;#80;ss=1;#200;expect_fault();
  if(dut.endpoint.accepted!=0)$fatal(1,"partial SPI stored a head");
  restart();push(0);logical_ready();
  for(int i=0;i<expanded;i++)begin
   bus_read('h400000+i,v);if(v!==view_data[i])$fatal(1,"cold row %d",i);
  end
  publish();if(fault||dut.endpoint.retired!=1)$fatal(1,"cold receipt");
  restart();stop=1;#40;stop=0;push(0);expect_fault();
  restart();push(0);for(int i=0;i<expanded;i++)bus_read('h400000+i,v);
  for(int i=0;i<12;i++)bus_write('h6010+i,ack[i]);
  stop=1;#45;stop=0;bus_write('h601c,'ha5);expect_fault();
  restart();push(0);bus_read('h400000,v);bus_read('h400000,v);expect_fault();
  restart();push(0);bus_read('h400011,v);expect_fault();
  restart();push(0);for(int i=0;i<17;i++)bus_read('h400000+i,v);publish();expect_fault();
  // A following SEAL cannot pass the partially consumed compact head.
  restart();push(0);previous_n=n;saved=wire_packet;n=16;
  wire_packet[0]=3;wire_packet[12]=0;push(0);n=previous_n;wire_packet=saved;
  if(dut.endpoint.accepted!=2 || fault)$fatal(1,"two queued packets");
  for(int i=0;i<17;i++)bus_read('h400000+i,v);
  if(fault)$fatal(1,"normal partial read failed");
  publish();expect_fault();
  restart();push(0);for(int i=0;i<17;i++)bus_read('h400000+i,v);stop=1;#80;expect_fault();
  restart();push(0);
  for(int i=0;i<expanded;i++)bus_read('h400000+i,v);
  ack[2]^=1;publish();expect_fault();ack[2]^=1;
  restart();push(0);for(int i=0;i<expanded;i++)bus_read('h400000+i,v);
  // The one-past-end byte must never drive, even if an address is held.
  address='h400000+expanded;#35;rn=0;#83;if(!oe)$fatal(1,"overread drove bus");rn=1;#65;expect_fault();
  restart();
 endtask
 reg [7:0] observed;
 reg [7:0] status_crc;
 initial begin
  if(!$value$plusargs("stim=%s",input_path)||!$value$plusargs("lut=%s",output_path))$fatal;
  stream=$fopen(input_path,"r");lut=$fopen(output_path,"w");if(!stream||!lut)$fatal;
  restart();cases=0;
  while($fscanf(stream,"%d",n)==1)begin
   if(n<34||n>70)$fatal;
   for(k=0;k<n;k++)if($fscanf(stream,"%h",wire_packet[k])!=1)$fatal;
   expanded=16+(n-16)/18*64;
   push(0);logical_ready();
   if($fscanf(stream,"%d",count)!=1)$fatal;
   for(k=0;k<count;k++)begin
    if($fscanf(stream,"%h %h",off,val)!=2)$fatal;
    bus_read('h400000+off,observed);if(observed!==val[7:0])$fatal(1,"view %d %d %h != %h",cases,off,observed,val);
    view_data[off]=observed;
   end
   for(k=0;k<12;k++)if($fscanf(stream,"%h",ack[k])!=1)$fatal;
   publish();
   ss=0;#100;for(k=0;k<20;k++)spi(k==0?'he0:0,status[k]);ss=1;#150;
   status_crc=0;
   for(k=1;k<=18;k++)begin
    status_crc^=status[k];
    repeat(8)status_crc=status_crc[7]?(status_crc<<1)^8'h07:status_crc<<1;
   end
   if(fault || status[19]!==status_crc || status[1]!=8'hf7 || !status[2][1] ||
      {status[3],status[4]}!=dut.endpoint.accepted || {status[5],status[6]}!=dut.endpoint.accepted ||
      status[8]!=9 || status[7]!=0)$fatal(1,"bad E0 receipt");
   for(k=2;k<12;k++)if(status[7+k]!==ack[k])$fatal(1,"bad E0 identity");
   for(k=0;k<n;k++)$fwrite(lut,"%02x",wire_packet[k]);$fwrite(lut," ");
   for(k=0;k<expanded;k++)$fwrite(lut,"%02x",view_data[k]);$fwrite(lut,"\n");
   if(!cases)negatives();
   cases++;
  end
  if(!cases)$fatal(1,"no vectors");
  $fclose(lut);$display("PASS829 actual DMA reads %0d packets; reject CRC/order/duplicate/short/STOP/identity/overread",cases);$finish;
 end
endmodule
