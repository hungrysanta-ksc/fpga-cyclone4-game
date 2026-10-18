// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rows245_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort_source=0,lease_ok=1,start=0;
 reg [8:0] entry=0;reg [15:0] argument0=0,argument1=0;
 wire start_ready,busy,done;wire [3:0] fault;
 wire [7:0] result,record_length;wire record_valid;reg record_ready=0;
 reg payload_valid=0,payload_write=0;reg [8:0] payload_address=0;reg [7:0] payload_data=0;
 wire payload_ready,payload_read_valid;wire [7:0] payload_q;
 wire byte_valid;reg byte_ready=0;wire [7:0] byte_data;
 nes_operand245 dut(.*);
 integer entries[0:31],fd,rf,cf,rc,ep,av,expected_result,n=0,i,j,k,ticks,cycle=0;
 integer expected_cases,expected_records,expected_bytes,records=0,bytes_seen=0,remaining=0,size,v;
 integer maximum[0:31],counts[0:31],which,blocked=0,cancels=0,rejected=0;
 reg [4095:0] before_mem,after_mem;
 reg [7:0] stopped[0:511];reg tracking=0,automatic_transport=1;
 reg held_byte=0,held_record=0;reg [7:0] held_data,held_length;
 always @(negedge clk)begin
  cycle=cycle+1;
  if(automatic_transport)begin record_ready=cycle%13!=0;byte_ready=cycle%7!=0&&cycle%512>=19;end
 end
 always @(posedge clk)begin
  if(!reset&&!abort_source&&lease_ok&&!fault)begin
   if(held_byte&&(!byte_valid||byte_data!==held_data))$fatal(1,"held byte changed");
   if(held_record&&(!record_valid||record_length!==held_length))$fatal(1,"held record changed");
   if(tracking)begin
    if(record_valid&&record_ready)begin
     if(remaining)$fatal(1,"overlap");rc=$fscanf(rf,"%d",size);
     if(rc!=1||size!==record_length)$fatal(1,"record length n=%0d",n);
     remaining=size;records=records+1;
    end
    if(byte_valid&&byte_ready)begin
     rc=$fscanf(rf,"%h",v);
     if(rc!=1||remaining<=0||byte_data!==v)$fatal(1,"record byte n=%0d byte=%0d got=%x expected=%x",n,bytes_seen,byte_data,v);
     remaining=remaining-1;bytes_seen=bytes_seen+1;
    end
   end
  end
  held_byte=!reset&&!abort_source&&lease_ok&&!fault&&byte_valid&&!byte_ready;held_data=byte_data;
  held_record=!reset&&!abort_source&&lease_ok&&!fault&&record_valid&&!record_ready;held_length=record_length;
 end
 task reboot;begin
  @(negedge clk);reset=1;start=0;abort_source=0;lease_ok=1;payload_valid=0;
  repeat(3)@(negedge clk);reset=0;
 end endtask
 task launch(input integer pc,input integer a);begin
  @(negedge clk);if(!start_ready)$fatal(1,"not ready");entry=pc;argument0=a;argument1=a>>16;start=1;
  @(negedge clk);start=0;entry=511;argument0=16'hdead;
 end endtask
 task finish_op;begin
  ticks=0;while(!done&&!fault&&ticks<20000)begin @(negedge clk);ticks=ticks+1;end
  if(fault||!done)$fatal(1,"fault n=%0d entry=%0d code=%0d",n,ep,fault);
  while(byte_valid||record_valid)begin @(negedge clk);ticks=ticks+1;if(ticks>=20000)$fatal(1,"drain timeout");end
 end endtask
 initial begin
  $readmemh("entries-base.hex",entries);
  for(i=0;i<32;i=i+1)begin maximum[i]=0;counts[i]=0;end
  cf=$fopen("rows-counts.txt","r");rc=$fscanf(cf,"%d %d %d",expected_cases,expected_records,expected_bytes);$fclose(cf);
  reboot();fd=$fopen("rows.txt","r");rf=$fopen("rows-records.txt","r");if(!fd||!rf)$fatal(1,"fixtures missing");tracking=1;
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %h %h\n",which,av,expected_result,before_mem,after_mem);if(rc!=5)$fatal(1,"malformed row fixture");
   if(which<100)for(i=0;i<512;i=i+1)dut.scratch[i]=before_mem[i*8+:8];
   else begin
    which=which-100;
    for(i=0;i<512;i=i+1)begin
     if(i<66||(i>=128&&i<194))begin
      @(negedge clk);payload_valid=1;payload_write=1;payload_address=i;payload_data=before_mem[i*8+:8];
      #1;if(!payload_ready)$fatal(1,"input port not ready");@(negedge clk);payload_valid=0;
     end else if(dut.scratch[i]!==before_mem[i*8+:8])$fatal(1,"continuous state was not preserved n=%0d address=%0d",n,i);
    end
   end
   ep=entries[which];launch(ep,av);finish_op();
   if(expected_result>=0&&result!==expected_result)$fatal(1,"row result n=%0d which=%0d got=%0d want=%0d",n,which,result,expected_result);
   for(i=0;i<512;i=i+1)if(dut.scratch[i]!==after_mem[i*8+:8])$fatal(1,"memory n=%0d entry=%0d at=%0d got=%x want=%x",n,ep,i,dut.scratch[i],after_mem[i*8+:8]);
   counts[which]=counts[which]+1;if(ticks>maximum[which])maximum[which]=ticks;n=n+1;
  end
  if(n!=expected_cases||records!=expected_records||bytes_seen!=expected_bytes||remaining)$fatal(1,"missing records");
  tracking=0;$fclose(fd);$fclose(rf);
  for(i=20;i<27;i=i+1)$display("ROW245 entry=%0d cases=%0d max_cycles=%0d",i,counts[i],maximum[i]);
  reboot();for(i=0;i<512;i=i+1)dut.scratch[i]=i;
  payload_valid=1;payload_write=0;payload_address=96;launch(entries[22],0);
  while(!done)begin #1;if(!payload_ready)blocked=blocked+1;@(negedge clk);end
  payload_valid=0;if(blocked!=1)$fatal(1,"mask B write/A read collision");
  // Invalid first cheap record or ROWPAIR mode must publish nothing. A later
  // abort cannot overwrite the original internal-contract fault.
  for(j=0;j<5;j=j+1)begin
   reboot();for(i=0;i<512;i=i+1)dut.scratch[i]=0;
   dut.scratch[120]=j==0?13:4;dut.scratch[82]=j==1?0:j==2?10:j==3?2:1;
   dut.program_rom[511]=(27<<13)|3;
   for(i=0;i<512;i=i+1)stopped[i]=dut.scratch[i];
   launch(j==4?511:entries[26],0);ticks=0;
   while(!fault&&ticks<500)begin
    if(record_valid||byte_valid)$fatal(1,"bad record published");@(negedge clk);ticks=ticks+1;
   end
   if(fault!==6||busy||record_valid||byte_valid)$fatal(1,"bad program/record accepted");
   for(i=0;i<512;i=i+1)if(dut.scratch[i]!==stopped[i])$fatal(1,"bad operation changed RAM");
   abort_source=1;repeat(3)@(negedge clk);if(fault!==6)$fatal(1,"first fault overwritten");rejected=rejected+1;
  end
  // Abort/lease at each new RAM phase, including the mask write edge.
  // Never permit an A write into row/M data while ROWPAIR owns it.
  automatic_transport=0;record_ready=0;byte_ready=0;
  for(j=0;j<2;j=j+1)for(k=0;k<5;k=k+1)begin
   reboot();for(i=0;i<512;i=i+1)dut.scratch[i]=i;
   launch(k==3?entries[21]:entries[22],0);
   ticks=0;
   while(!(dut.opcode==27&&dut.phase==(k==0?1:k==1?2:k==2?3:k==3?4:5))&&ticks<500)begin @(negedge clk);ticks=ticks+1;end
   if(ticks==500)$fatal(1,"phase missing %0d",k);
   payload_valid=1;payload_write=1;payload_address=k==4?96:128;payload_data=99;
   #1;if(payload_ready)$fatal(1,"row ownership missing");blocked=blocked+1;
   for(i=0;i<512;i=i+1)stopped[i]=dut.scratch[i];
   if(j==0)abort_source=1;else lease_ok=0;
   @(negedge clk);payload_valid=0;
   if(fault!==(j==0?4:2)||busy||byte_valid||record_valid)$fatal(1,"cancel failure");
   for(i=0;i<512;i=i+1)if(dut.scratch[i]!==stopped[i])$fatal(1,"write on cancellation edge");
   repeat(5)@(negedge clk);
   for(i=0;i<512;i=i+1)if(dut.scratch[i]!==stopped[i])$fatal(1,"post-cancel write");
   cancels=cancels+1;
  end
  $display("PASS ROWS245 cases=%0d records=%0d bytes=%0d row_owner_block=%0d cancels=%0d rejected=%0d",n,records,bytes_seen,blocked,cancels,rejected);$finish;
 end
 initial begin #500000000;$fatal(1,"watchdog");end
endmodule
