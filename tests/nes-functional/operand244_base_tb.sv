// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Prepared RF operation fixtures, not a bound encoder or game simulation.
module operand244_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort_source=0,lease_ok=1,start=0;
 reg [8:0] entry=0;reg [15:0] argument0=0,argument1=0;
 wire start_ready,busy,done;wire [3:0] fault;
 wire [7:0] result,record_length;wire record_valid;reg record_ready=1;
 reg payload_valid=0,payload_write=0;reg [8:0] payload_address=0;reg [7:0] payload_data=0;
 wire payload_ready,payload_read_valid;wire [7:0] payload_q;
 wire byte_valid;reg byte_ready=0;wire [7:0] byte_data;
 nes_operand244 dut(.*);
 integer entries[0:31];integer fd,rc,cmd,a,b,n=0,i,j,ticks,maximum=0;
 reg [191:0] before_rf,after_rf;
 reg [7:0] snapshot[0:23];
 task reboot;begin
  @(negedge clk);reset=1;start=0;abort_source=0;lease_ok=1;payload_valid=0;byte_ready=0;
  repeat(3)@(negedge clk);reset=0;
 end endtask
 task launch(input integer ep,input integer av,input integer bv);begin
  @(negedge clk);if(!start_ready)$fatal(1,"not ready");
  entry=ep;argument0=av;argument1=bv;start=1;
  @(negedge clk);start=0;argument0=16'hdead;argument1=16'hbeef;entry=511;
 end endtask
 task finish_op;begin
  ticks=0;
  while(!done&&!fault&&ticks<600)begin @(negedge clk);ticks=ticks+1;end
  if(fault||!done)$fatal(1,"kernel fault/timeout n=%0d fault=%0d",n,fault);
  if(ticks>maximum)maximum=ticks;
 end endtask
 task payload_store(input integer at,input integer value);begin
  @(negedge clk);payload_valid=1;payload_write=1;payload_address=at;payload_data=value;
  #1;if(!payload_ready)$fatal(1,"payload blocked");
  @(negedge clk);payload_valid=0;
 end endtask
 initial begin
  $readmemh("entries-base.hex",entries);
  reboot();
  for(i=0;i<512;i=i+1)dut.scratch[i]=8'ha5;
  // All payload addresses remain available; RF aliases are refused.
  for(i=0;i<512;i=i+1)begin
   if(i<104||i>=128)payload_store(i,i^8'h39);
   else begin
    @(negedge clk);payload_valid=1;payload_write=1;payload_address=i;payload_data=0;
    #1;if(payload_ready)$fatal(1,"RF alias accepted");
    @(negedge clk);payload_valid=0;
    if(dut.scratch[i]!==8'ha5)$fatal(1,"RF alias wrote");
   end
  end
  for(i=0;i<512;i=i+1)if(i<104||i>=128)begin
   @(negedge clk);payload_valid=1;payload_write=0;payload_address=i;
   @(negedge clk);
   if(!payload_read_valid||payload_q!==((i^8'h39)&255))$fatal(1,"payload synchronous read %0d",i);
   payload_valid=0;
   @(negedge clk);if(payload_read_valid)$fatal(1,"stale read valid");
  end
  fd=$fopen("vectors-base.txt","r");if(!fd)$fatal(1,"vectors missing");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %h %h %h %h\n",cmd,a,b,before_rf,after_rf);
   if(rc!=5)$fatal(1,"bad vector");
   for(i=0;i<24;i=i+1)dut.scratch[104+i]=before_rf[i*8+:8];
   launch(entries[cmd],a,b);finish_op();
   for(i=0;i<24;i=i+1)if(dut.scratch[104+i]!==after_rf[i*8+:8])
    $fatal(1,"RF mismatch n=%0d cmd=%0d address=%0d got=%x expected=%x",n,cmd,104+i,dut.scratch[104+i],after_rf[i*8+:8]);
   n=n+1;
  end
  $fclose(fd);
  // No operand operation may touch any of the payload addresses.
  for(i=0;i<512;i=i+1)if(i<104||i>=128)
   if(dut.scratch[i]!==((i^8'h39)&255))$fatal(1,"payload damaged at %0d",i);
  launch(entries[7],8'h6a,16'h8357);
  while(!byte_valid)@(negedge clk);
  // First OUT stays held while later operand writes complete and next OUT stalls.
  for(j=0;j<64;j=j+1)begin
   payload_store(208+(j%20),j);
   if(!byte_valid||byte_data!==8'h6a)$fatal(1,"published byte changed");
  end
  if(dut.scratch[124]!==8'h57||dut.scratch[125]!==8'h83||!busy||done)$fatal(1,"stalled output prevented RF work");
  @(negedge clk);byte_ready=1;
  @(negedge clk);byte_ready=0;
  while(!done)@(negedge clk);
  if(!byte_valid||byte_data!==8'h57||start_ready)$fatal(1,"second output/ownership");
  @(negedge clk);byte_ready=1;@(negedge clk);byte_ready=0;
  if(byte_valid||!start_ready)$fatal(1,"output drain");
  // Abort/lease loss at every cycle of the longest init operation. Partial
  // writes are invalidated; common reset plus INIT is required before reuse.
  for(j=0;j<2;j=j+1)for(i=0;i<2*(entries[1]-entries[0]);i=i+1)begin
   reboot();launch(entries[0],1792,0);repeat(i)@(negedge clk);
   if(j==0)abort_source=1;else lease_ok=0;
   @(negedge clk);
   if(fault!==(j==0?4:2)||busy||byte_valid)$fatal(1,"cancel phase j=%0d i=%0d",j,i);
   for(ticks=0;ticks<24;ticks=ticks+1)snapshot[ticks]=dut.scratch[104+ticks];
   abort_source=1;lease_ok=0;repeat(3)@(negedge clk);
   for(ticks=0;ticks<24;ticks=ticks+1)if(snapshot[ticks]!==dut.scratch[104+ticks])$fatal(1,"write after cancel");
   if(fault!==(j==0?4:2))$fatal(1,"first fault overwritten");
  end
  for(j=8;j<10;j=j+1)begin
   reboot();launch(entries[j],0,0);repeat(12)@(negedge clk);
   if(fault!==6||busy)$fatal(1,"bad program not refused");
  end
  reboot();launch(entries[7],8'h55,0);while(!byte_valid)@(negedge clk);
  lease_ok=0;@(negedge clk);if(byte_valid||fault!==2)$fatal(1,"lease retained publication");
  reboot();launch(entries[7],8'h55,0);while(!byte_valid)@(negedge clk);
  abort_source=1;@(negedge clk);if(byte_valid||fault!==4)$fatal(1,"abort retained publication");
  reboot();launch(entries[7],8'h55,0);while(!byte_valid)@(negedge clk);
  reset=1;@(negedge clk);if(byte_valid||busy||fault)$fatal(1,"reset retained publication");
  $display("PASS OPERAND244_BASE vectors=%0d max_operation_cycles=%0d payload_write_read=488 RF_aliases=24 cancel_phases=%0d held_output=128 bad_program=2 publication_cancel=3",n,maximum,4*(entries[1]-entries[0]));
  $finish;
 end
 initial begin #100000000;$fatal(1,"global watchdog");end
endmodule
