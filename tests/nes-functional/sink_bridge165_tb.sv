// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module sink_bridge165_tb;
 parameter real PHASE=0;
 reg clk=0,reset=1,active=1,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;reg rn=1,wn=1,romsel=1;reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault;wire [7:0] dout;wire [15:0] pads;
 nes_sink_bridge165 dut(clk,reset,active,stop,ss,sck,mosi,selected,miso,address,rn,wn,romsel,din,dout,oe,dir,pc,pads,fault);
 always #5.952 clk=~clk;
 reg [7:0] packets[0:58111],acks[0:2723],program_bytes[0:4095];
 reg [8:0] lengths[0:226];reg [7:0] tx[0:258],rx[0:258];
 integer i,j,n,fd,wirebytes=0,pc_count=0,checks=0;reg trace_on=1;reg [7:0] value;
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;integer k;begin c=c0^b;for(k=0;k<8;k++)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer k;begin c=c0^{b,8'd0};for(k=0;k<8;k++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 task transfer(input integer size);
  integer k,b;begin
   #2000;ss=0;#2000;
   for(k=0;k<size;k++)begin rx[k]=0;for(b=7;b>=0;b--)begin
    mosi=tx[k][b];#190.476;sck=1;rx[k][b]=selected?miso:0;#190.476;sck=0;
   end end
   #2000;ss=1;#1;if(selected)$fatal(1,"raw SPI release");#1999;
   if(trace_on)begin
    $fwrite(fd,"%0d ",size);for(k=0;k<size;k++)$fwrite(fd,"%02x",tx[k]);$fwrite(fd," ");
    for(k=0;k<size;k++)$fwrite(fd,"%02x",rx[k]);$fwrite(fd,"\n");wirebytes+=size;
   end
  end
 endtask
 task status;
  integer k;reg [7:0] c;begin
   for(k=0;k<16;k++)tx[k]=0;tx[0]=8'he0;transfer(16);
   c=0;for(k=1;k<15;k++)c=c8(c,rx[k]);
   if(rx[1]!=8'hf6||rx[15]!=c)$fatal(1,"status CRC %02x/%02x",rx[15],c);
  end
 endtask
 task prepare(input integer index);
  integer k;reg [15:0] c;begin
   tx[0]=8'he1;c=c16(16'hffff,tx[0]);
   for(k=0;k<lengths[index];k++)begin tx[k+1]=packets[index*256+k];c=c16(c,tx[k+1]);end
   tx[lengths[index]+1]=c[15:8];tx[lengths[index]+2]=c[7:0];
  end
 endtask
 task read_byte(input [23:0] a,input [7:0] expected);
  begin address=a;romsel=!a[15]||a[23:16]!=0;rn=0;wn=1;#100;
   if(oe||!dir||dout!==expected)$fatal(1,"read %06x got %02x expected %02x oe%d",a,dout,expected,oe);
   checks++;
  end
 endtask
 task release_read;
  begin rn=1;#1;if(!oe||dir)$fatal(1,"raw read release");#99;end
 endtask
 task write_byte(input [23:0] a,input [7:0] b);
  begin address=a;romsel=1;rn=1;wn=0;din=~b;#50;din=b;#100;wn=1;#1;
   if(!oe||dir)$fatal(1,"raw write release");#99;
  end
 endtask
 task common_reset;
  begin ss=1;sck=0;rn=1;wn=1;reset=1;#100;reset=0;#100;end
 endtask
 always @(posedge clk)if(pc)pc_count<=pc_count+1;
 initial begin
  $readmemh("packets.hex",packets);$readmemh("acks.hex",acks);$readmemh("lengths.hex",lengths);
  $readmemh("sink-program.hex",program_bytes);fd=$fopen("transactions.txt","w");
  #100;reset=0;#(PHASE);#100;
  // Full4KiB image: body beyond old2KiB, vector mirror, unmapped holes.
  for(i=0;i<4032;i++)read_byte(24'h008000+i,program_bytes[i]);
  for(i=0;i<64;i++)read_byte(24'h00ffc0+i,program_bytes[4032+i]);
  read_byte(24'h009000,8'hff);release_read;
  write_byte(24'h006002,8'h80);write_byte(24'h006003,8'h04);
  if(pads!=16'h0480||pc_count!=1)$fatal(1,"late write sample/pad double commit");
  for(n=0;n<227;n++)begin
   if(n==137)common_reset;
   status;if(rx[2][7:2]!=0||rx[2][0])$fatal(1,"not free");
   prepare(n);transfer(lengths[n]+3);
   if(fault||!dut.ready||dut.length!=lengths[n])$fatal(1,"not admitted %d",n);
   // Read arbitrary/header offsets then continuous DMA-like addresses with /RD held.
   read_byte(24'h006004,lengths[n][7:0]);read_byte(24'h006005,{7'd0,lengths[n][8]});release_read;
   for(j=0;j<lengths[n];j++)read_byte(24'h400000+j,packets[n*256+j]);
   if(lengths[n]<256)begin address=24'h400000+lengths[n];#100;if(!oe)$fatal(1,"out-of-packet drive");end
   release_read;
   if(n==0)begin
    for(j=0;j<12;j++)write_byte(24'h006010+j,acks[n*12+j]);
    // Publication during a status transfer must not tear its old snapshot/CRC.
    fork status;begin #12000;write_byte(24'h00601c,8'ha5);end join
   end else begin
    status;
    for(j=0;j<12;j++)write_byte(24'h006010+j,acks[n*12+j]);
    write_byte(24'h00601c,8'ha5);
   end
   if(rx[2]!=1)$fatal(1,"busy status snapshot");
   status;if(rx[2]!=2||dut.ready||fault)$fatal(1,"ACK retirement");
   for(j=0;j<12;j++)if(rx[j+3]!==acks[n*12+j])$fatal(1,"ACK byte %d",j);
  end
  $fclose(fd);trace_on=0;
  // STOP register and raw disable must not drive another owner's bus.
  stop=1;read_byte(24'h006001,8'h80);active=0;#1;if(!oe||dir)$fatal(1,"raw inactive");release_read;active=1;stop=0;
  common_reset;status;if(rx[2]!=0)$fatal(1,"reset leaked ACK");
  prepare(0);tx[lengths[0]+2]^=1;transfer(lengths[0]+3);if(!fault||dut.ready)$fatal(1,"bad CRC admitted");
  common_reset;prepare(0);transfer(lengths[0]+2);if(!fault||dut.ready)$fatal(1,"truncation admitted");
  common_reset;prepare(0);transfer(lengths[0]+3);prepare(1);transfer(lengths[1]+3);
  if(!fault)$fatal(1,"owned overwrite accepted");
  for(j=0;j<lengths[0];j++)if(dut.endpoint.buffer[j]!==packets[j])$fatal(1,"owned byte overwritten");
  common_reset;prepare(0);transfer(lengths[0]+3);write_byte(24'h006010,0);write_byte(24'h00601c,8'ha5);
  if(!fault||dut.endpoint.ack_valid)$fatal(1,"partial ACK published");
  common_reset;tx[0]=8'hd0;for(j=1;j<16;j++)tx[j]=0;transfer(16);
  if(fault||dut.ready)$fatal(1,"foreign family mutation");
  common_reset;prepare(0);transfer(lengths[0]+3);address=24'h400000;rn=0;#100;
  reset=1;#1;if(!oe||dir||selected)$fatal(1,"raw reset drive");#99;reset=0;rn=1;#100;
  status;if(rx[2]!=0)$fatal(1,"reset retained packet");
  $display("PASS SINKBRIDGE165 packets=227 bytechecks=%0d wirebytes=%0d phase=%0f",checks,wirebytes,PHASE);$finish;
 end
 initial begin #500000000;$fatal(1,"bridge watchdog");end
endmodule
