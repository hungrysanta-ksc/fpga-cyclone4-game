// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module pulse577_tb;
 reg mem_clk=0,reset=1,load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0,commands_blocked=0;
 reg [7:0] load_data=8'ha5;
 always #2976 mem_clk=!mem_clk;
 nes_rom_loader dut(.mem_clk(mem_clk),.reset(reset),.load_begin(load_begin),.load_chr32(load_chr32),
  .load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.commands_blocked(commands_blocked),.load_data(load_data));
 integer tests=0,writes=0,total_writes=0,end_faults=0,blocked_end=0;
 time driven_at,write_at,write_min=64'hffffffffffffffff,setup_min=64'hffffffffffffffff,hold_min=64'hffffffffffffffff;
 reg in_write=0,had_write=0;
 always @(posedge dut.load_drive)driven_at=$time;
 always @(negedge dut.load_we)begin
  if(reset)$fatal(1,"write during reset");
  if($time-driven_at<22*5952)$fatal(1,"short SETUP");
  if($time-driven_at<setup_min)setup_min=$time-driven_at;
  write_at=$time;in_write=1;had_write=1;writes++;total_writes++;
 end
 always @(posedge dut.load_we)if(in_write)begin
  if(reset||$time-write_at<64*5952)$fatal(1,"short WRITE");
  if($time-write_at<write_min)write_min=$time-write_at;
  in_write=0;write_at=$time;
 end
 always @(negedge dut.load_drive)if(had_write)begin
  if($time-write_at<22*5952)$fatal(1,"short HOLD");
  if($time-write_at<hold_min)hold_min=$time-write_at;
  had_write=0;
 end
 always @(negedge mem_clk)if(!dut.load_we)begin
  if(dut.load_pin_data!==16'ha5a5||dut.load_address!==0||dut.load_1ce!==0||dut.load_2ce!==1||dut.load_oe!==1)
   $fatal(1,"accepted write pins changed");
 end
 initial begin
  if($test$plusargs("SHIFT"))#1300;
  for(integer offset=0;offset<130;offset++)for(integer command=0;command<64;command++)begin
   @(negedge mem_clk);
   reset=1;{commands_blocked,load_begin,load_valid,load_end,start,stop}=0;writes=0;
   repeat(3)@(negedge mem_clk);reset=0;repeat(4)@(negedge mem_clk);
   load_begin=1;@(negedge mem_clk);load_begin=0;
   if(!dut.load_ready)$fatal(1,"BEGIN not accepted");
   load_valid=1;@(negedge mem_clk);load_valid=0;
   repeat(offset)@(negedge mem_clk);
   {commands_blocked,load_begin,load_valid,load_end,start,stop}=command;
   @(posedge mem_clk);#1;
   if(command==4)begin
    if(!dut.fault)$fatal(1,"busy END not rejected offset=%0d",offset);
    end_faults++;
   end
   if(command==36)begin
    if(dut.fault)$fatal(1,"blocked END changed state");
    blocked_end++;
   end
   @(negedge mem_clk);{commands_blocked,load_begin,load_valid,load_end,start,stop}=0;
   repeat(170)@(negedge mem_clk);
   if(in_write||had_write||writes>1)$fatal(1,"write drain did not finish once");
   tests++;
  end
  if(tests!=8320||end_faults!=130||blocked_end!=130)$fatal(1,"coverage");
  $display("PASS577 cases=%0d writes=%0d busy_END=%0d blocked_END=%0d setup_ps=%0t write_ps=%0t hold_ps=%0t",
   tests,total_writes,end_faults,blocked_end,setup_min,write_min,hold_min);
  $finish;
 end
 initial begin #(64'd100000000000);$fatal(1,"watchdog");end
endmodule
