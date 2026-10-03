`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg reset=1,run=0,en=1,gr=1,lw=0,rw=0,snap=0,mr=0,mw=0,sc=0;
reg[7:0]cd=0,md=0;reg[3:0]rs=8,ma=0;reg[63:0]sd=0;
wire[7:0]cr,mout;wire done,dirty,watchdog;wire[28:0]sb;
gbc_mbc3_rtc #(.SECOND_CYCLES(128)) dut(clk,reset,run,en,gr,lw,cd,rw,rs,cr,1'b1,mr,mw,ma,md,done,mout,sc,sd,sb,dirty,watchdog);
integer n;reg[28:0]saved;integer phase_model=0;
 always @(posedge clk)begin
  if(reset)phase_model=0;
  else begin
   if(watchdog!==(phase_model==7))$fatal(1,"watchdog phase altered by game/host RTC writes");
   phase_model=(phase_model+1)%8;
  end
 end
task tick;begin @(posedge clk);#1;end endtask
task put(input[3:0]a,input[7:0]v);begin ma=a;md=v;mw=1;tick();mw=0;tick();end endtask
task latch;begin cd=0;lw=1;tick();lw=0;tick();cd=1;lw=1;tick();lw=0;tick();end endtask
task check(input[3:0]a,input[7:0]v);begin rs=a;#1;if(cr!==v)$fatal(1,"RTC select %d actual %h expected %h",a,cr,v);end endtask
task write_reg(input[3:0]a,input[7:0]v);begin rs=a;cd=v;rw=1;#1;if(!dirty)$fatal(1,"RTC dirty missing");tick();rw=0;tick();end endtask
initial begin
 repeat(3)tick();reset=0;
 put(0,59);put(1,59);put(2,23);put(3,255);put(4,1);
 run=1;gr=0;latch();check(8,59);check(12,1);
 repeat(128)tick();check(8,59); // latched values stay stable
 latch();check(8,0);check(9,0);check(10,0);check(11,0);check(12,128);
 write_reg(12,64);latch();check(12,64);repeat(400)tick();latch();check(8,0);
 write_reg(8,17);write_reg(9,42);write_reg(10,13);write_reg(11,7);latch();
 check(8,17);check(9,42);check(10,13);check(11,7);check(12,64);
 // 0,2,1 must NOT latch; only adjacent 0->1.
 write_reg(8,22);cd=0;lw=1;tick();cd=2;tick();cd=1;tick();lw=0;tick();check(8,17);latch();check(8,22);
 snap=1;tick();snap=0;write_reg(8,33);
 ma=0;mr=1;tick();if(mout!==33)$fatal(1,"live read");ma=8;tick();if(mout!==22)$fatal(1,"latched read");mr=0;tick();
 // State restores latch and edge-detector, battery clock remains live.
 saved=sb;latch();check(8,33);sd={19'b0,saved,16'b0};sc=1;tick();sc=0;check(8,22);latch();check(8,33);
 // Game reset preserves battery/latched data; speed/pause have no RTC clock input.
 gr=1;repeat(3)tick();gr=0;latch();check(8,33);check(12,64);
 write_reg(12,0);repeat(128)tick();latch();check(8,34);
 // Host cannot overwrite a running battery clock.
 put(0,55);latch();check(8,34);
 en=0;rs=8;#1;if(cr!==255)$fatal(1,"plain MBC3 RTC open bus");
 $display("PASS RTC rollover carry halt writes 0-to-1 latch snapshot state reset run-write guard");$finish;
end
endmodule
