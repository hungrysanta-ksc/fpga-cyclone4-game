// Exercise both low-byte carries, including511->512, through actual SPI ACKs.
fresh();loaded_bytes=512;open_check();
for(integer a=0;a<512;a++)begin command(8'h67,a,0);command(8'h68,a,a^8'ha5);end
command(8'h69,512,0);ck(dut.check_next==512&&dut.verified&&!fault,"CARRY128 512 ordered ACKs");
// Seed large indices to exercise the split counter across64KiB and the two
// diagnostic image ends without claiming a full80/96KiB SPI replay.
for(integer boundary=0;boundary<3;boundary++)begin
 integer index128;
 index128=boundary==0?65535:boundary==1?81919:98303;
 fresh();loaded_bytes=98304;open_check();
 @(negedge mem_clk);dut.check_next=index128;#200;
 command(8'h67,index128,0);command(8'h68,index128,index128^8'ha5);
 ck(dut.check_next==index128+1&&!fault,"CARRY128 seeded large boundary");
end
// A valid queued START must lose to a newly observed hard fault.
verified128();
begin
 integer before_start;before_start=starts128;
 fork
  command(8'h63,16,0);
  begin wait(dut.pending);#0.001;check_fault=1;end
 join
 ck(fault&&error_code==9&&!run_enable&&starts128==before_start,"RETIRE128 hard fault wins START");
end
// A sub-cycle raw reset clears the queued transaction through the actual local
// reset helper. Clock stoppage cannot release reset or resurrect the command.
verified128();
begin
 integer before_start;before_start=starts128;
 fork
  command(8'h63,16,0);
  begin
   wait(dut.pending);#0.001;mem_running128=0;raw_reset=1;#0.010;
   ck(reset&&!dut.pending&&!start&&!check_enable,"RETIRE128 async cancel");
   raw_reset=0;#50;ck(reset&&!start,"RETIRE128 stopped-clock hold");
   mem_running128=1;
  end
 join
 ck(starts128==before_start&&!run_enable&&!dut.pending,"RETIRE128 no stale START");
end
// One synchronized SS-high cycle queues a valid BEGIN but starts another frame
// before retirement. Reject it rather than committing two transactions.
fresh();
begin
 integer before_begin;before_begin=begins128;
 fork
  command(8'h60,0,0);
  begin @(posedge SPI_SS);#5.952;SPI_SS=0;#100;SPI_SS=1;end
 join
 ck(fault&&error_code==1&&begins128==before_begin,"RETIRE128 overlapping frame");
end
$display("PASS128 boundary hard_fault_start=1 raw_reset_pending=1 clock_stop=1 overlapping_frame=1");
