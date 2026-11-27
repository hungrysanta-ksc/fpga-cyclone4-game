`timescale 1ns/1ns
module ff3_chr_group1051_tb;
 reg clk=0,reset=1,changed=0,start=0,discard=0,retire=0,export_reset=1;
 reg [5:0] group_id=0;
 reg [15:0] generation=0,retired=0;
 wire fine,stable,can_start,ready,tx_valid;
 wire [7:0] receipt;
 wire [95:0] tx;
 always #5 clk=!clk;
 nes_chr_snapshot snapshot(.clk(clk),.reset(reset),.changed(changed),.changed_group(group_id),
  .start(start),.start_gen(generation),.collecting(1'b0),.discard(discard),.retire(retire),
  .retire_gen(retired),.fine_receipt(fine),.frame_unchanged(stable),.clean_pages(receipt),
  .ready(ready),.can_start(can_start),.scan_data(8'h0),.read_req(1'b0),.cancel(1'b0),
  .read_addr(18'd0),.read_gen(16'd0),.ram_q(8'd0));
 nes_native_export203 exporter(.clk(clk),.reset(export_reset),.enable(1'b1),.start_permitted(1'b1),
  .discard_permitted(1'b1),.frame_owned(ready),.frame_generation(generation),
  .geometry_valid(1'b1),.row_count(8'd224),.group_count(6'd1),.palette_count(6'd1),
  .object_count(8'd0),.exception_count(8'd0),.patch_count(3'd0),.fine_receipt(fine),
  .clean_pages(receipt),.chr_unchanged(stable),.tx_ready(1'b0),.tx_valid(tx_valid),.tx_data(tx),
  .ack_valid(1'b0),.ack_accept(1'b0),.ack_generation(16'd0),.response(1'b0),.hit(1'b0),.data(64'd0));
 task tick; @(negedge clk); endtask
 task capture(input bit narrow,input reg [7:0] expected);
  while(!can_start) tick;
  generation=generation+1;start=1;tick;start=0;
  export_reset=0;tick;
  if(!tx_valid || tx[92:77]!==generation || tx[63:48]!==(narrow?16'h2235:16'h2234)
     || tx[11:4]!==expected || tx[3]!==(&expected)) $fatal(1,"bad receipt %h expected %h",tx,expected);
  export_reset=1;tick;
 endtask
 task release_frame;
  retired=generation;retire=1;tick;retire=0;
 endtask
 task write_group(input reg [5:0] which_group);
  changed=1;group_id=which_group;tick;changed=0;
 endtask
 initial begin
  tick;reset=0;capture(0,0);release_frame;
  for(integer g=0;g<64;g=g+1) begin
   write_group(g);write_group(g);capture(1,g);release_frame;
  end
  write_group(4);write_group(5);capture(0,8'hfe);
  retired=generation-1'b1;retire=1;tick;retire=0;
  if(!ready) $fatal(1,"stale retire released owner");
  write_group(15);changed=1;group_id=16;release_frame;changed=0;
  capture(0,8'hf9);release_frame;capture(0,8'hff);
  write_group(4);discard=1;tick;discard=0;capture(0,8'hfe);release_frame;
  write_group(63);reset=1;tick;reset=0;capture(0,0);release_frame;
  $display("PASS1051 64 narrow headers, wide, cold, stale retire, retire-edge write and discard");
  $finish;
 end
 initial begin #12000000; $fatal(1,"timeout"); end
endmodule
