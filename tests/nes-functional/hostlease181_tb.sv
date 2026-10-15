// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module hostlease181_tb;
 reg clk=0,clock_run=1,reset=1,active=0,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;reg rn=1,wn=1,romsel=1;reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault;wire [7:0] dout;wire [15:0] pads;
 nes_sink_bridge165 dut(clk,reset,active,stop,ss,sck,mosi,selected,miso,address,rn,wn,romsel,din,dout,oe,dir,pc,pads,fault);
 always #5.952381 if(clock_run)clk=~clk;
 reg [7:0] tx[0:258],rx[0:258];integer i,j,phase,mode,checks=0,commits=0,cancels=0;
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer k;begin c=c0^{b,8'd0};for(k=0;k<8;k++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;integer k;begin c=c0^b;for(k=0;k<8;k++)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 task transfer(input integer size);
  integer k,b;begin
   #2000;ss=0;#2000;
   for(k=0;k<size;k++)begin rx[k]=0;for(b=7;b>=0;b--)begin
    mosi=tx[k][b];#190.476;sck=1;rx[k][b]=selected?miso:0;#190.476;sck=0;
   end end
   #2000;ss=1;#1;if(selected)$fatal(1,"SPI raw deselect");#1999;
  end
 endtask
 task status(input [7:0] flags);
  integer k;reg [7:0] crc;begin
   for(k=0;k<16;k++)tx[k]=0;tx[0]=8'he0;transfer(16);
   crc=0;for(k=1;k<15;k++)crc=c8(crc,rx[k]);
   if(rx[1]!=8'hf6||rx[2]!=flags||rx[15]!=crc)$fatal(1,"status expected %x got %x crc %x/%x",flags,rx[2],rx[15],crc);
   checks++;
  end
 endtask
 task send_packet;
  integer k;reg [15:0] crc;begin
   tx[0]=8'he1;for(k=1;k<=16;k++)tx[k]=k;tx[13]=0;tx[14]=0;
   crc=16'hffff;for(k=0;k<=16;k++)crc=c16(crc,tx[k]);tx[17]=crc[15:8];tx[18]=crc[7:0];
   transfer(19);if(fault||!dut.ready||dut.length!=16)$fatal(1,"packet not admitted");checks++;
  end
 endtask
 task write_byte(input [23:0] a,input [7:0] b);
  begin address=a;romsel=1;rn=1;wn=0;din=b;#150;wn=1;#100;end
 endtask
 task ack_bytes(input integer count);
  integer k;begin for(k=0;k<count;k++)write_byte(24'h006010+k,8'h40+k);end
 endtask
 task complete;
  integer k;begin
   send_packet;status(1);
   for(k=0;k<16;k++)begin address=24'h400000+k;rn=0;#100;
    if(oe||!dir||dout!==(k==12||k==13?8'd0:k+1))$fatal(1,"packet read %d got %x",k,dout);
   end
   rn=1;#100;ack_bytes(12);write_byte(24'h00601c,8'ha5);status(2);
   for(k=0;k<12;k++)if(rx[k+3]!==8'h40+k)$fatal(1,"ACK value");commits++;
  end
 endtask
 task no_owner;
  begin #0.1;if(!oe||dir||selected||pc)$fatal(1,"raw cancellation outputs");
   if(dut.ready||dut.endpoint.ack_valid||dut.endpoint.ack_mask||dut.endpoint.sealed)$fatal(1,"cancel retained packet/ACK");
   checks++;cancels++;
  end
 endtask
 task restart;
  begin ss=1;sck=0;rn=1;wn=1;address=0;stop=0;active=1;reset=0;#150;
   if(!dut.host_ready||fault)$fatal(1,"host failed admission");status(0);
  end
 endtask
 initial begin
  #100;reset=0;
  for(phase=0;phase<16;phase++)begin
   #37;active=0;#(phase*0.375);no_owner;
   // A RUN rise cannot adopt a transaction/write already in progress.
   ss=0;wn=0;address=24'h00601c;din=8'ha5;active=1;#200;
   if(dut.host_ready||!oe||dir||selected)$fatal(1,"admission inside old transaction");
   ss=1;#100;if(dut.host_ready)$fatal(1,"admission inside old write");
   wn=1;#150;if(!dut.host_ready||fault||dut.endpoint.ack_valid)$fatal(1,"idle admission");status(0);complete;
   // Transport errors still latch; graceful stop remains readable by client.
   stop=1;address=24'h006001;rn=0;#100;
   if(oe||dout!=8'h80)$fatal(1,"graceful STOP register");rn=1;stop=0;
   for(mode=0;mode<6;mode++)begin
    active=0;#20;restart;send_packet;
    if(mode==1)ack_bytes(5);
    if(mode>=2)ack_bytes(12);
    if(mode==3)begin
     // Cancel between bus ACK-byte publication and endpoint consumption.
     fork write_byte(24'h006010,8'h99);begin wait(dut.aw);#1;active=0;no_owner;end join
    end else if(mode==4)begin
     fork write_byte(24'h00601c,8'ha5);begin wait(dut.ap);#1;active=0;no_owner;end join
    end else if(mode==5)begin
     // Cancel a coherent status snapshot in progress; next run must be empty.
     for(j=0;j<16;j++)tx[j]=0;tx[0]=8'he0;
     fork transfer(16);begin #12000;active=0;no_owner;end join
    end else begin address=24'h400000;rn=0;#100;active=0;no_owner;end
    #50;restart;complete;
   end
   // The host clock can stop with a packet owned. Raw reset still revokes it.
   active=0;#20;restart;send_packet;address=24'h400000;rn=0;#100;
   @(negedge clk);clock_run=0;reset=1;no_owner;#100;reset=0;#100;
   if(dut.host_ready||!oe||dir)$fatal(1,"clock stopped release");
   rn=1;clock_run=1;#150;status(0);complete;
   // Partial ACK is still a fault, not an accepted generation.
   active=0;#20;restart;send_packet;ack_bytes(1);write_byte(24'h00601c,8'ha5);
   if(!fault||dut.endpoint.ack_valid)$fatal(1,"partial ACK accepted");
   active=0;#20;restart;
  end
  $display("PASS HOSTLEASE181 phases=16 commits=%0d cancels=%0d checks=%0d",commits,cancels,checks);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
