// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Actual206 bulk+batch+mailboxes. External cancel while either clock is stopped.
// Full/partial RAM and sealed plan ownership; no physical metastability model.
module cancel206_tb;
 reg n=0,h=0,nrun=1,hrun=1,rst=1,stop=0,sfault=0;
 always #23 if(nrun)n=!n;
 always #6 if(hrun)h=!h;
 reg tv=0,ev=0;reg [4:0] idx=0;wire ready,er,chunk,bfault;wire [11:0] clen;
 wire [31:0] token;wire [7:0] d;wire oe,dir;
 nes_tile_bulk206 bulk(.nes_clk(n),.host_clk(h),.reset(rst),.active(1'b1),.stop(stop),.source_fault(sfault),
 .tile_valid(tv),.tile_ready(ready),.tile_data({3'd0,idx}),.tile_index(idx),.tile_length(6'd16),.tile_kind(2'd0),.tile_slot(10'd1),.tile_generation(16'd7),
 .end_valid(ev),.end_ready(er),.end_generation(16'd7),.token_seed(32'd1),
 .chunk_ready(chunk),.chunk_length(clen),.chunk_token(token),.chunk_kind(),.chunk_slot(),.chunk_generation(),
 .consume(1'b0),.consume_token(32'd0),.consume_error(),.address(24'h400800),.read_n(1'b0),.write_n(1'b1),
 .data_out(d),.oe_n(oe),.dir(dir),.fault(bfault),.end_sealed(),.sealed_generation());
 reg wv=0,seal=0;reg [7:0] wd=0;reg [15:0] crc=0;wire wr,pi,pv,ef,pfault;
 nes_plan_batch206 batch(.host_clk(h),.nes_clk(n),.reset(rst),.active(1'b1),.stop(stop),.source_fault(sfault),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.retire(1'b0),.retire_done(),.retire_permitted(1'b0),.retire_commit(),
 .seal(seal),.seal_length(10'd3),.seal_plans(5'd1),.seal_crc(crc),.host_idle(pi),.fault(pfault),
 .lease_valid(1'b1),.lease_generation(16'd7),.plan_valid(pv),.plan_ready(1'b0),.tile_done(1'b0),.plan_kind(),.plan_generation(),
 .plan_slot(),.plan_tag(),.plan_rows(),.plan_mask(),.plan_alt_mask(),.plan_alt_tags(),.end_valid(ef),.end_ready(1'b0),.end_generation());
 task nt;begin @(posedge n);#1;end endtask
 task ht;begin @(posedge h);#1;end endtask
 task fresh;
  begin rst=1;nrun=1;hrun=1;stop=0;sfault=0;tv=0;ev=0;wv=0;seal=0;idx=0;
   repeat(4)nt();@(negedge n);rst=0;repeat(20)nt();
   if(!ready||!wr||chunk||pv||bfault||pfault)$fatal(1,"fresh state");end
 endtask
 task put_tile(input integer count);
  begin for(integer j=0;j<count;j++)begin
   while(!ready)nt();@(negedge n);idx=5'(j);tv=1;nt();@(negedge n);tv=0;
  end end
 endtask
 task put_plan(input bit bad_crc);
  begin crc=16'hffff;
   for(integer j=0;j<3;j++)begin
    while(!wr)ht();@(negedge h);wd=j==0?8'h82:j==1?8'd7:8'd0;
    crc=batch.crc16(crc,wd);wv=1;ht();@(negedge h);wv=0;
   end
   crc=crc^(bad_crc?16'd1:16'd0);seal=1;ht();@(negedge h);seal=0;
  end
 endtask
 task hidden;
  begin #0.01;if(chunk||!oe||dir||pv||ef||ready||wr||bulk.word_valid||batch.word_valid)
   $fatal(1,"ownership survived cancellation");end
 endtask
 integer checks=0;
 initial begin
  for(integer full=0;full<2;full++)for(integer cause=0;cause<3;cause++)for(integer paused=0;paused<3;paused++)begin
   fresh();put_tile(full?16:7);put_plan(0);wait(pv);
   if(full)begin while(!er)nt();@(negedge n);ev=1;nt();@(negedge n);ev=0;wait(chunk);if(clen!=16)$fatal(1,"not sealed");end
   @(negedge n);@(negedge h);nrun=paused==1;hrun=paused==0;
   if(cause==0)rst=1;else if(cause==1)stop=1;else sfault=1;
   #1;hidden();#200;rst=0;stop=0;sfault=0;
   // Still stopped: source/destination readiness must not reappear on either
   // side. The running side may leave local reset but waits for peer up.
   #200;if(chunk||pv||ef||bulk.word_valid||batch.word_valid)$fatal(1,"stopped-clock replay");
   nrun=1;hrun=1;repeat(20)nt();
   if(chunk||pv||ef||bfault||pfault||!ready||!wr)$fatal(1,"cancel recovery");checks++;
  end
  fresh();put_tile(7);@(negedge n);idx=9;tv=1;nt();@(negedge n);tv=0;
  repeat(8)nt();if(!bfault||ready||chunk||bulk.word_valid)$fatal(1,"bulk local fault not sticky");checks++;
  fresh();put_plan(1);repeat(8)nt();if(!pfault||wr||pv||batch.word_valid)$fatal(1,"batch local fault not sticky");checks++;
  fresh();put_tile(16);while(!er)nt();@(negedge n);ev=1;nt();@(negedge n);ev=0;wait(chunk);
  if(clen!=16||token!=1)$fatal(1,"fresh tile after faults");checks++;
  $display("PASS CANCEL206 checks=%0d",checks);$finish;
 end
 initial begin #2000000;$fatal(1,"watchdog");end
endmodule
