// SPDX-License-Identifier: MIT
// bus/rd_n/wr_n share the pin-level SNES driver with test571.
task latency571;
 time changed,elapsed;
 integer edges;
 restart();memory_open=1;
 $readmemh("fresh.hex",raw,0,17);data_frame(0,18);wait(dut.chunk_ready);
 read571(24'h400800,8'h63);
 for(int phase=0;phase<4;phase++)begin
  @(negedge host_clk);
  case(phase)
   0:#1;
   1:#5951;
   2:#5953;
   3:#11903;
  endcase
  // Sample after NBA, on every capture edge, from addresses whose RAM
  // tags differ. Only the third edge may publish the newly addressed byte.
  changed=$time;bus=24'h400801+phase;#0;
  if(!SNES_DATABUS_OE||SNES_DATABUS_DIR||SNES_DATA!==8'hzz)$fatal(1,"stale tag");
  for(edges=1;edges<=3;edges++)begin
   @(posedge host_clk);#1;
   if(edges<3)sample571(1,0,8'hzz);
   else if(SNES_DATABUS_OE||!SNES_DATABUS_DIR||SNES_DATA!==8'h63)$fatal(1,"capture edge");
  end
  elapsed=$time-changed;
  $display("LAT571 phase=%0d elapsed_ps=%0d",phase,elapsed);
 end
 rd_n=1;sample571(1,0,8'hzz);$display("PASS571 LAT");$finish;
endtask
