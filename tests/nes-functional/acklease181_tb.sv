// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module acklease181_tb;
 reg clk=0,reset=1,enable=1,ss=1,sck=0,mosi=0;
 reg aw=0,ap=0;reg [3:0] ai=0;reg [7:0] ab=0;
 wire selected,miso,ready,fault,bs,bm,br,bf;wire [8:0] length,bl;wire [7:0] data,bd;
 nes_sink_spi165 dut(clk,reset,enable,ss,sck,mosi,selected,miso,8'd0,data,ready,length,aw,ai,ab,ap,fault);
 nes_sink_spi165_reference old(clk,reset,enable,ss,sck,mosi,bs,bm,8'd0,bd,br,bl,aw,ai,ab,ap,bf);
 always #5.952381 clk=~clk;
 reg [7:0] tx[0:258],rx[0:258],rr[0:258];
 integer i,j,phase,mode,checks=0,exchanges=0,trace,case_id=-1,seed=0;
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer k;begin c=c0^{b,8'd0};for(k=0;k<8;k++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;integer k;begin c=c0^b;for(k=0;k<8;k++)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 task transfer(input integer size);
  integer k,b;begin
   #2000;ss=0;#2000;
   for(k=0;k<size;k++)begin rx[k]=0;rr[k]=0;for(b=7;b>=0;b--)begin
    mosi=tx[k][b];#190.476;sck=1;rx[k][b]=selected?miso:0;rr[k][b]=bs?bm:0;#190.476;sck=0;
   end end
   #2000;ss=1;#2000;
   if(case_id>=0)begin
    $fwrite(trace,"%0d %0d",case_id,size);
    for(k=0;k<size;k++)$fwrite(trace," %02x",tx[k]);
    for(k=0;k<size;k++)$fwrite(trace," %02x",rx[k]);$fwrite(trace,"\n");
   end
  end
 endtask
 task status_tx;
  integer k;begin for(k=0;k<16;k++)tx[k]=0;tx[0]=8'he0;transfer(16);end
 endtask
 task check_status(input [7:0] flags);
  integer k;reg [7:0] crc,bc;begin
   crc=0;bc=0;for(k=1;k<15;k++)begin crc=c8(crc,rx[k]);bc=c8(bc,rr[k]);end
   if(rx[1]!=8'hf6||rx[2]!=flags||rx[15]!=crc||rr[1]!=8'hf6||rr[2]!=flags||rr[15]!=bc)
    $fatal(1,"status/CRC flags %x got %x/%x",flags,rx[2],rr[2]);
   for(k=0;k<12;k++)begin
    if(flags[1])begin if(rx[k+3]!==rr[k+3]||rx[k+3]!==((seed+k)&255))$fatal(1,"valid ACK mismatch %d",k);end
    else if(rx[k+3]!==0)$fatal(1,"invalid ACK exposed work");
   end
   checks++;
  end
 endtask
 task packet(input integer corrupt);
  integer k;reg [15:0] crc;begin
   tx[0]=8'he1;for(k=1;k<=16;k++)tx[k]=k;tx[13]=0;tx[14]=0;
   crc=16'hffff;for(k=0;k<=16;k++)crc=c16(crc,tx[k]);tx[17]=crc[15:8];tx[18]=crc[7:0]^corrupt;
   transfer(19);if(!corrupt&&(fault||!ready||length!=16))$fatal(1,"packet admission");
  end
 endtask
 task write_ack(input integer lo,hi);
  integer k;begin for(k=lo;k<hi;k++)begin @(negedge clk);ai=k;ab=seed+k;aw=1;@(negedge clk);aw=0;end end
 endtask
 task restart;
  begin reset=1;aw=0;ap=0;ss=1;sck=0;#100;reset=0;#100;end
 endtask
 // E0 command's final synchronized rising edge is the snapshot event.
 task publish_at_snapshot(input integer when_edge);
  begin
   wait(!dut.ss[1]&&dut.bit_count==7&&dut.byte_count==0);
   wait(dut.sck[0]&&!dut.sck[1]);
   @(negedge clk);
   if(when_edge>=0)@(negedge clk);
   if(when_edge>0)@(negedge clk);
   ap=1;@(negedge clk);ap=0;
  end
 endtask
 initial begin
  trace=$fopen("wire.txt","w");if(!trace)$fatal(1,"trace open");
  for(phase=0;phase<16;phase++)for(mode=-1;mode<=1;mode++)begin
   case_id=-1;restart;#(phase*0.375);seed=32+phase*9+mode+1;case_id=exchanges;
   status_tx;check_status(0);packet(0);
   write_ack(0,5);status_tx;check_status(1);
   write_ack(5,12);status_tx;check_status(1);
   fork status_tx;publish_at_snapshot(mode);join
   check_status(mode<0?2:1);
   if(mode>=0)begin status_tx;check_status(2);end
   if(fault||bf||ready||br)$fatal(1,"completion state");
   exchanges++;case_id=-1;
   // Next packet invalidates the old ACK, and mid-status writes stay invisible.
   packet(0);seed=seed+17;
   fork status_tx;begin #15000;write_ack(0,12);end join
   check_status(1);@(negedge clk);ap=1;@(negedge clk);ap=0;
   status_tx;check_status(2);
  end
  // The actual bus cannot issue both pulses. Preserve old-data publication
  // defensively even if a direct endpoint user repeats one byte concurrently.
  restart;packet(0);seed=75;write_ack(0,12);
  @(negedge clk);aw=1;ai=0;ab=8'hee;ap=1;@(negedge clk);aw=0;ap=0;
  status_tx;check_status(2);
  restart;packet(0);write_ack(0,11);@(negedge clk);ap=1;@(negedge clk);ap=0;
  if(!fault||!bf||dut.ack_valid)$fatal(1,"partial publish accepted");
  restart;packet(1);if(!fault||!bf||ready)$fatal(1,"CRC bad packet accepted");
  restart;packet(0);@(negedge clk);aw=1;ai=12;@(negedge clk);aw=0;
  if(!fault||!bf)$fatal(1,"out of range accepted");
  restart;status_tx;check_status(0);
  $fclose(trace);$display("PASS ACKLEASE181 exchanges=%0d checks=%0d",exchanges,checks);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
