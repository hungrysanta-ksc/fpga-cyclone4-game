// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Continuous literal state and exact bytes. This is not the outer240 encoder.
module literal244_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort_source=0,lease_ok=1,start=0;
 reg [8:0] entry=0;reg [15:0] argument0=0,argument1=0;
 wire start_ready,busy,done;wire [3:0] fault;
 wire [7:0] result,record_length;wire record_valid;reg record_ready=0;
 reg payload_valid=0,payload_write=0;reg [8:0] payload_address=0;reg [7:0] payload_data=0;
 wire payload_ready,payload_read_valid;wire [7:0] payload_q;
 wire byte_valid;reg byte_ready=0;wire [7:0] byte_data;
 nes_operand244 dut(.*);
 integer entries[0:31];integer fd,rf,af,cf,rc,ep,av,bv,expect_result,n=0,i,j,k,ticks,cycles=0,max_cycles=0;
 integer expected_commands,expected_records,expected_bytes,expected_append,expected_flush,flush_count=0;
 integer record_count=0,byte_count=0,left_bytes=0,packet_size,expected_byte,append_count=0,at,blocked=0,cancel_count=0;
 reg [191:0] expected_rf,pre_rf;reg [95:0] expected_c;reg [1919:0] expected_l;
 reg [95:0] pre_c;reg [1919:0] pre_l;reg [1943:0] fixture_packet;
 integer fixture_length,fixture_bytes=0,fixture_records=0,flush_records=0,flush_bytes=0;
 reg fixture_tracking=0;
 reg [7:0] stopped[0:511];reg tracking=0,automatic_transport=1;
 reg held_byte=0,held_record=0;reg [7:0] held_data,held_length;
 always @(negedge clk)begin
  cycles=cycles+1;
  if(automatic_transport)begin
   byte_ready=cycles%7!=0&&cycles%4096>=64;
   record_ready=cycles%11!=0&&cycles%2048>=32;
  end
 end
 always @(posedge clk)begin
  if(!reset&&!abort_source&&lease_ok&&!fault)begin
   if(held_byte&&(!byte_valid||byte_data!==held_data))$fatal(1,"byte changed under stall");
   if(held_record&&(!record_valid||record_length!==held_length))$fatal(1,"record changed under stall");
   if(tracking)begin
    if(record_valid&&record_ready)begin
     if(left_bytes)$fatal(1,"record overlaps previous bytes");
     rc=$fscanf(rf,"%d",packet_size);if(rc!=1||record_length!==packet_size)$fatal(1,"record length mismatch");
     left_bytes=packet_size;record_count=record_count+1;
    end
    if(byte_valid&&byte_ready)begin
     if(left_bytes<=0)$fatal(1,"byte without record");
     rc=$fscanf(rf,"%h",expected_byte);if(rc!=1||byte_data!==expected_byte)$fatal(1,"byte mismatch at %0d",byte_count);
     left_bytes=left_bytes-1;byte_count=byte_count+1;
    end
   end
   if(fixture_tracking)begin
    if(record_valid&&record_ready)begin
     if(record_length!==fixture_length||fixture_records)$fatal(1,"actual240 flush length");
     fixture_records=fixture_records+1;
    end
    if(byte_valid&&byte_ready)begin
     if(fixture_records!=1||fixture_bytes>=fixture_length||byte_data!==fixture_packet[fixture_bytes*8+:8])$fatal(1,"actual240 flush bytes");
     fixture_bytes=fixture_bytes+1;
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
 task launch(input integer pc,input integer a,input integer b);begin
  @(negedge clk);if(!start_ready)$fatal(1,"not ready");entry=pc;argument0=a;argument1=b;start=1;
  @(negedge clk);start=0;argument0=16'hdead;argument1=16'hbeef;entry=511;
 end endtask
 task finish_op;begin
  ticks=0;
  while(!done&&!fault&&ticks<20000)begin @(negedge clk);ticks=ticks+1;end
  if(fault||!done)$fatal(1,"fault/timeout n=%0d ep=%0d fault=%0d",n,ep,fault);
  while(byte_valid||record_valid)begin @(negedge clk);ticks=ticks+1;if(ticks>=20000)$fatal(1,"drain timeout");end
  if(ticks>max_cycles)max_cycles=ticks;
 end endtask
 initial begin
  $readmemh("entries-base.hex",entries);
  cf=$fopen("expected_counts.txt","r");rc=$fscanf(cf,"%d %d %d %d %d",expected_commands,expected_records,expected_bytes,expected_append,expected_flush);$fclose(cf);
  reboot();for(i=0;i<512;i=i+1)dut.scratch[i]=8'ha5;for(i=104;i<128;i=i+1)dut.scratch[i]=0;
  fd=$fopen("lifecycle.txt","r");rf=$fopen("records.txt","r");if(!fd||!rf)$fatal(1,"missing fixtures");tracking=1;
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %h %h %d %h %h %h\n",ep,av,bv,expect_result,expected_rf,expected_c,expected_l);
   if(rc!=7)$fatal(1,"malformed lifecycle fixture");
   launch(ep,av,bv);finish_op();
   if(expect_result>=0&&result!==expect_result)$fatal(1,"result n=%0d ep=%0d got=%0d want=%0d",n,ep,result,expect_result);
   for(i=0;i<24;i=i+1)if(dut.scratch[104+i]!==expected_rf[i*8+:8])$fatal(1,"RF n=%0d ep=%0d at=%0d got=%x want=%x",n,ep,104+i,dut.scratch[104+i],expected_rf[i*8+:8]);
   for(i=0;i<12;i=i+1)if(dut.scratch[80+i]!==expected_c[i*8+:8])$fatal(1,"cheap payload n=%0d at=%0d",n,80+i);
   for(i=0;i<240;i=i+1)if(dut.scratch[256+i]!==expected_l[i*8+:8])$fatal(1,"literal payload n=%0d at=%0d",n,256+i);
   n=n+1;
  end
  if(n!=expected_commands||record_count!=expected_records||byte_count!=expected_bytes||left_bytes)$fatal(1,"incomplete stream");
  tracking=0;$fclose(fd);$fclose(rf);
  // Prepared RF cases sampled from actual240, separate from the continuous run.
  af=$fopen("append.txt","r");if(!af)$fatal(1,"append fixtures missing");
  while(!$feof(af))begin
   rc=$fscanf(af,"%h %h %d %h %h %d\n",av,bv,expect_result,pre_rf,expected_rf,at);if(rc!=6)$fatal(1,"append fixture malformed");
   for(i=0;i<24;i=i+1)dut.scratch[104+i]=pre_rf[i*8+:8];
   for(i=256;i<496;i=i+1)dut.scratch[i]=8'ha5;
   launch(entries[11],av,bv);finish_op();
   if(result!==expect_result)$fatal(1,"observed append result");
   for(i=0;i<24;i=i+1)if(dut.scratch[104+i]!==expected_rf[i*8+:8])$fatal(1,"observed append RF");
   for(i=0;i<240;i=i+1)if(dut.scratch[256+i]!==((i==at)?av:8'ha5))$fatal(1,"observed append payload");
   append_count=append_count+1;
  end
  if(append_count!=expected_append)$fatal(1,"append count");$fclose(af);
  af=$fopen("flush.txt","r");if(!af)$fatal(1,"flush fixtures missing");
  while(!$feof(af))begin
   rc=$fscanf(af,"%h %d %h %h %h %h %h %h %d %h\n",bv,expect_result,pre_rf,expected_rf,pre_c,pre_l,expected_c,expected_l,fixture_length,fixture_packet);
   if(rc!=10)$fatal(1,"flush fixture malformed");
   for(i=0;i<24;i=i+1)dut.scratch[104+i]=pre_rf[i*8+:8];
   for(i=0;i<12;i=i+1)dut.scratch[80+i]=pre_c[i*8+:8];
   for(i=0;i<240;i=i+1)dut.scratch[256+i]=pre_l[i*8+:8];
   fixture_bytes=0;fixture_records=0;fixture_tracking=1;
   launch(entries[12],0,bv);finish_op();fixture_tracking=0;
   if(result!==expect_result||fixture_bytes!=fixture_length||fixture_records!=(fixture_length!=0))$fatal(1,"observed flush result");
   for(i=0;i<24;i=i+1)if(dut.scratch[104+i]!==expected_rf[i*8+:8])$fatal(1,"observed flush RF at=%0d case=%0d",i,flush_count);
   for(i=0;i<12;i=i+1)if(dut.scratch[80+i]!==expected_c[i*8+:8])$fatal(1,"observed flush cheap bytes");
   for(i=0;i<240;i=i+1)if(dut.scratch[256+i]!==expected_l[i*8+:8])$fatal(1,"observed flush literal bytes");
   flush_count=flush_count+1;flush_records=flush_records+fixture_records;flush_bytes=flush_bytes+fixture_bytes;
  end
  if(flush_count!=expected_flush)$fatal(1,"flush count");$fclose(af);
  // B write beats A read to same address; nonconflicting A remains available.
  reboot();payload_valid=1;payload_write=0;payload_address=261;
  launch(entries[16],5,8'h66);
  while(!done)begin
   #1;if(!payload_ready)blocked=blocked+1;
   @(negedge clk);
  end
  payload_valid=0;if(blocked!=1||dut.scratch[261]!==8'h66)$fatal(1,"B/A collision arbitration");
  automatic_transport=0;byte_ready=0;record_ready=0;
  launch(entries[17],5,0);payload_valid=1;payload_write=1;payload_address=261;payload_data=8'hff;
  while(!done)begin #1;if(payload_ready)$fatal(1,"owned literal write accepted");@(negedge clk);end
  payload_valid=0;if(!byte_valid||byte_data!==8'h66||dut.scratch[261]!==8'h66)$fatal(1,"pending byte ownership");
  repeat(64)@(negedge clk);byte_ready=1;@(negedge clk);byte_ready=0;
  for(j=18;j<20;j=j+1)begin
   reboot();launch(entries[j],0,0);repeat(25)@(negedge clk);if(fault!==6||busy)$fatal(1,"bad indirect address accepted");
  end
  // Stop at RF writes, payload writes, RAM read, record stall and byte stall.
  for(j=0;j<2;j=j+1)for(k=0;k<5;k=k+1)begin
   reboot();for(i=104;i<128;i=i+1)dut.scratch[i]=0;dut.scratch[116]=4;
   if(k==1)begin dut.scratch[115]=0;dut.scratch[126]=0;launch(entries[11],1,0);end
   else launch(entries[12],0,0);
   ticks=0;
   while(!((k==0&&dut.operand_write&&!dut.indirect)||(k==1&&dut.operand_write&&dut.indirect)||
           (k==2&&dut.phase==2)||(k==3&&record_valid)||(k==4&&byte_valid))&&ticks<10000)begin
    if(k<3||k==4)record_ready=1;
    if(k<3)byte_ready=1;
    @(negedge clk);ticks=ticks+1;
   end
   if(ticks==10000)$fatal(1,"cancel point missing %0d",k);
   if(j==0)abort_source=1;else lease_ok=0;
   @(negedge clk);if(busy||byte_valid||record_valid||fault!==(j==0?4:2))$fatal(1,"cancel did not clear");
   for(i=0;i<512;i=i+1)stopped[i]=dut.scratch[i];
   repeat(5)@(negedge clk);
   for(i=0;i<512;i=i+1)if(dut.scratch[i]!==stopped[i])$fatal(1,"write after stop");
   cancel_count=cancel_count+1;byte_ready=0;record_ready=0;
  end
  $display("PASS LITERAL244 commands=%0d records=%0d bytes=%0d actual_append=%0d actual_flush=%0d/%0drecords/%0dbytes max_cycles=%0d collision_block=%0d live_cancel=%0d",n,record_count,byte_count,append_count,flush_count,flush_records,flush_bytes,max_cycles,blocked,cancel_count);
  $finish;
 end
 initial begin #500000000;$fatal(1,"global watchdog");end
endmodule
