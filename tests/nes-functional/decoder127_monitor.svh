// CHECK comparisons must match live inputs at every applicable retirement.
// Offset settles at byte3; index changes only on retired ACK, length is held.
always @(posedge mem_clk)if(!reset && dut.ss_sync[1] && !dut.ss_previous && dut.ours && !fault && dut.byte_count==8 && dut.bit_count==0)begin
 if(dut.command==8'h67 || dut.command==8'h68)
  if(dut.offset_matches_next !== (dut.offset=={7'd0,dut.check_next}))$fatal(1,"PIPE127 stale offset/index");
 if(dut.command==8'h67 && dut.next_below_length !== (dut.check_next<loaded_bytes))$fatal(1,"PIPE127 stale bound");
 if(dut.command==8'h69 && dut.next_matches_length !== (dut.check_next==loaded_bytes))$fatal(1,"PIPE127 stale length");
end
