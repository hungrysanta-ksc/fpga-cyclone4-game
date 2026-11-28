`timescale 1ns/1ps
module page_receipt1058_tb;
 reg clk=0,rst=1,wr=0,start=0,finish=0,retire=0,discard=0,en=0;
 reg [5:0] group_id=0;
 reg [15:0] gen=0;
 wire [7:0] mask;
 wire fine,conflict,ready;
 always #5 clk=!clk;
 nes_chr_snapshot s(.clk(clk),.reset(rst),.changed(wr),.changed_group(group_id),
    .start(start),.capture_end(finish),.collecting(1'b1),.rendering(en),
    .retire(retire),.discard(discard),.start_gen(gen),.retire_gen(gen),
    .clean_pages(mask),.fine_receipt(fine),.read_req(1'b0),.cancel(1'b0),
    .conflict(conflict),.ready(ready),.scan_data(8'hc3),.ram_q(8'hc3));
 task tick;begin @(posedge clk);#1;end endtask
 task put(input [5:0] group_addr);begin group_id=group_addr;wr=1;tick();wr=0;end endtask
 task begin_capture;begin gen=gen+1;start=1;tick();start=0;end endtask
 task seal;begin repeat(52000)tick();finish=1;tick();finish=0;if(!ready || conflict)$fatal(1,"unclean seal");end endtask
 task ack;begin retire=1;tick();retire=0;end endtask
 initial begin
  tick();rst=0;begin_capture();seal();if(mask!==0)$fatal(1,"cold reuse");ack();
  // Battletoads stage prefix spans groups 0..2, 47 and 48 (pages 0,5,6).
  put(47);put(48);put(0);begin_capture();put(1);put(2);seal();
  if(fine || mask!==8'h9e)$fatal(1,"prefix mask %h",mask);
  // A write after sealing belongs to the next generation, including ACK edge.
  put(16);if(mask!==8'h9e)$fatal(1,"sealed receipt changed");
  wr=1;group_id=24;ack();wr=0;begin_capture();put(32);seal();
  if(fine || (mask & 8'h1d))$fatal(1,"reused dirty page %h",mask);
  ack();begin_capture();en=1;tick();put(8);if(!conflict)$fatal(1,"visible write");
  discard=1;tick();discard=0;rst=1;tick();if(ready)$fatal(1,"STOP");
  $display("PASS_PAGE1058 cold, stage 5 clean pages, sealed receipt, retire writes, visible conflict and STOP");$finish;
 end
endmodule
