// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module sink_window184_tb;
 parameter real PHASE=0;
 parameter integer WRAP=0;
 reg clk=0,reset=1,active=1,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;reg rn=1,wn=1,romsel=1;reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault;wire [7:0] dout;wire [15:0] pads;
 nes_sink_bridge165 dut(clk,reset,active,stop,ss,sck,mosi,selected,miso,address,rn,wn,romsel,din,dout,oe,dir,pc,pads,fault);
 always #5.952 clk=~clk;
 reg [7:0] tx[0:258],rx[0:258],packet[0:32][0:255],acks[0:32][0:11];
 integer lengths[0:32];integer i,j,k,n,fd,checks=0,calls=0,wirebytes=0,head=0,sent=0,retired=0;
 reg trace_on=1;reg [15:0] crc;
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;integer x;begin c=c0^b;for(x=0;x<8;x++)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer x;begin c=c0^{b,8'd0};for(x=0;x<8;x++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 task transfer(input integer size);
  integer x,b;begin
   #2000;ss=0;#2000;
   for(x=0;x<size;x++)begin rx[x]=0;for(b=7;b>=0;b--)begin
    mosi=tx[x][b];#190.476;sck=1;rx[x][b]=selected?miso:0;#190.476;sck=0;
   end end
   #2000;ss=1;#1;if(selected)$fatal(1,"raw SS output");#1999;
   if(trace_on)begin
    $fwrite(fd,"%0d ",size);for(x=0;x<size;x++)$fwrite(fd,"%02x",tx[x]);$fwrite(fd," ");
    for(x=0;x<size;x++)$fwrite(fd,"%02x",rx[x]);$fwrite(fd,"\n");calls++;wirebytes+=size;
   end
  end
 endtask
 task status;
  integer x;reg [7:0] c;begin
   for(x=0;x<20;x++)tx[x]=0;tx[0]=8'he0;transfer(20);
   c=0;for(x=1;x<19;x++)c=c8(c,rx[x]);
   if(rx[1]!=8'hf7||rx[19]!=c)$fatal(1,"status snapshot CRC");checks++;
  end
 endtask
 task prepare(input integer index);
  integer x;reg [15:0] c;begin
   tx[0]=8'he1;c=c16(16'hffff,tx[0]);
   for(x=0;x<lengths[index];x++)begin tx[x+1]=packet[index][x];c=c16(c,tx[x+1]);end
   tx[lengths[index]+1]=c[15:8];tx[lengths[index]+2]=c[7:0];
  end
 endtask
 task send_packet(input integer index);
  begin prepare(index);transfer(lengths[index]+3);if(fault)$fatal(1,"enqueue %d",index);end
 endtask
 task read_byte(input [23:0] a,input [7:0] expected);
  begin address=a;rn=0;wn=1;#100;
   if(oe||!dir||dout!==expected)$fatal(1,"bus %06x %02x != %02x",a,dout,expected);checks++;
  end
 endtask
 task release_read;begin rn=1;#100;end endtask
 task write_byte(input [23:0] a,input [7:0] b);
  begin address=a;rn=1;wn=0;din=b;#150;wn=1;#100;end
 endtask
 task inspect(input integer index);
  integer x;begin
   if(!dut.ready)$fatal(1,"missing head");
   read_byte(24'h006004,lengths[index]&255);read_byte(24'h006005,lengths[index]>>8);release_read;
   for(x=0;x<lengths[index];x++)read_byte(24'h400000+x,packet[index][x]);release_read;
  end
 endtask
 task consume(input integer index);
  integer x;begin
   inspect(index);
   for(x=0;x<12;x++)write_byte(24'h006010+x,acks[index][x]);
   write_byte(24'h00601c,8'ha5);#500;
   if(fault)$fatal(1,"ACK %d",index);
  end
 endtask
 task common_reset;
  begin ss=1;sck=0;rn=1;wn=1;stop=0;reset=1;#100;reset=0;#200;end
 endtask
 initial begin
  for(i=0;i<33;i++)begin
   lengths[i]=i==0?16:i==32?40:i%3==1?256:18;
   for(j=0;j<256;j++)packet[i][j]=(i*19+j*37)&255;
   packet[i][0]=i==0?1:i==32?3:i%3==1?2:i%3==2?4:5;
   packet[i][1]=0;packet[i][2]=i;packet[i][3]=0;
   packet[i][4]=1;packet[i][5]=0;packet[i][6]=0;packet[i][7]=0;
   packet[i][8]=8'h34;packet[i][9]=8'h12;packet[i][10]=0;packet[i][11]=0;
   packet[i][12]=lengths[i]-16;packet[i][13]=0;packet[i][14]=i%3==2?240:0;packet[i][15]=(i!=0&&i!=32&&i%3==0)?2:0;
   acks[i][0]=i==32?1:0;acks[i][1]=packet[i][0];
   for(j=2;j<10;j++)acks[i][j]=packet[i][j];acks[i][10]=8'h65;acks[i][11]=8'h9a;
  end
  fd=$fopen("transactions.txt","w");#100;reset=0;#(PHASE);#200;
  status;
  // Counter-wrap boundary injection only; packet traffic/ACK still use buses.
  if(WRAP)begin dut.endpoint.accepted=16'hfffc;dut.endpoint.retired=16'hfffc;end
  send_packet(0);consume(0);status;sent=1;retired=1;
  for(i=1;i<32;i++)begin
   if(sent-retired==4)begin consume(retired);consume(retired+1);retired=retired+2;status;end
   send_packet(i);sent=sent+1;
  end
  while(retired<sent)begin consume(retired);retired=retired+1;end
  status;send_packet(32);consume(32);status;
  if({rx[3],rx[4]}!=(WRAP?16'd29:16'd33)||{rx[5],rx[6]}!={rx[3],rx[4]}||rx[2]!=2)$fatal(1,"drain counters");
  $fclose(fd);trace_on=0;
  // Full queue cannot overwrite head, including a rejected fifth packet.
  common_reset;for(i=0;i<4;i++)send_packet(i);
  status;if(rx[2]!=5)$fatal(1,"full flags");inspect(0);
  prepare(4);transfer(lengths[4]+3);if(!fault||dut.endpoint.accepted!=4||dut.endpoint.retired!=0)$fatal(1,"full write");
  for(j=0;j<lengths[0];j++)if(dut.endpoint.buffer[j]!=packet[0][j])$fatal(1,"head overwritten");
  // CRC/short/invalid length never publishes a packet.
  common_reset;prepare(1);tx[lengths[1]+2]=tx[lengths[1]+2]^1;transfer(lengths[1]+3);
  if(!fault||dut.endpoint.accepted!=0)$fatal(1,"bad CRC publish");
  common_reset;prepare(1);transfer(18);if(!fault||dut.endpoint.accepted!=0)$fatal(1,"short publish");
  common_reset;prepare(1);tx[13]=241;transfer(lengths[1]+3);if(!fault||dut.endpoint.accepted!=0)$fatal(1,"length publish");
  // All ACK fields must validate before credit is returned.
  for(i=0;i<12;i++)begin
   common_reset;send_packet(0);send_packet(1);
   for(j=0;j<12;j++)write_byte(24'h006010+j,acks[0][j]^(i==j?1:0));
   write_byte(24'h00601c,8'ha5);#500;
   if(!fault||dut.endpoint.retired!=0||dut.ready)$fatal(1,"bad ACK byte %d",i);checks++;
  end
  common_reset;send_packet(0);for(j=0;j<11;j++)write_byte(24'h006010+j,acks[0][j]);
  write_byte(24'h00601c,8'ha5);if(!fault)$fatal(1,"partial ACK");
  common_reset;write_byte(24'h006010,0);if(!fault)$fatal(1,"ACK without head");
  // Consumer retirement may overlap producer SPI and status snapshot creation.
  common_reset;send_packet(0);
  fork send_packet(1);begin #12000;consume(0);end join
  if(dut.endpoint.accepted!=2||dut.endpoint.retired!=1)$fatal(1,"overlap counts");inspect(1);
  fork status;begin #12000;consume(1);end join
  if(rx[2]!=3||{rx[5],rx[6]}!=1)$fatal(1,"snapshot torn");status;if(rx[2]!=2)$fatal(1,"snapshot next");
  // STOP holds queue; COMMON reset clears ownership without RAM reset.
  send_packet(2);stop=1;read_byte(24'h006001,8'h80);release_read;
  if(dut.endpoint.retired!=2)$fatal(1,"STOP auto-retired");
  reset=1;#1;if(!oe||selected||dut.ready)$fatal(1,"raw reset output");#100;reset=0;#200;
  status;if(rx[2]||{rx[3],rx[4],rx[5],rx[6]})$fatal(1,"reset counters");
  // COMMON cancellation during a partial SPI packet must not admit its tail.
  common_reset;prepare(1);
  fork transfer(lengths[1]+3);begin
   #17000;if(dut.ready||dut.endpoint.accepted!=0)$fatal(1,"unsealed visible");
   reset=1;#100;reset=0;
  end join
  #200;if(dut.ready||fault||dut.endpoint.accepted!=0)$fatal(1,"stale SPI tail");
  send_packet(0);consume(0);
  // Cancel while the shared RAM port checks a completed ACK.
  send_packet(1);for(j=0;j<12;j++)write_byte(24'h006010+j,acks[1][j]);
  write_byte(24'h00601c,8'ha5);
  if(!dut.endpoint.checking)$fatal(1,"missed checking reset boundary");
  reset=1;#100;reset=0;#200;status;
  if(rx[2]||{rx[3],rx[4],rx[5],rx[6]})$fatal(1,"stale ACK release");
  // Legacy 16-byte E0 is incompatible and fail-closed.
  tx[0]=8'he0;transfer(16);if(!fault)$fatal(1,"old client accepted");
  $display("PASS WINDOW184 calls=%0d wirebytes=%0d checks=%0d packets=33 wrap=%0d",calls,wirebytes,checks,WRAP);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
