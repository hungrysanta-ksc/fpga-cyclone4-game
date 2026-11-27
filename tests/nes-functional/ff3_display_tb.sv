// Exercise the board profile's actual tile execution path with async cartridge SRAM.
`timescale 1ns/1ps
module ff3_display_tb;
 reg clk=0;always #23 clk=!clk;
 reg reset=1,stop=0,changed=0,start=0,collecting=0,discard=0,retire=0,owned=0,plan_valid=0;
 reg [2:0] changed_page;
 reg [15:0] gen=10,retire_gen=10;
 reg [1:0] kind=0;
 reg [13:0] tag=511; reg [15:0] fixture[34]; integer source_frame;
 reg [7:0] live[8192],physical[8192],scan_data,expected[16];
 wire [18:0] ram_addr;
 wire [12:0] scan_addr;
 wire oe_n,we_n,drive_data,can_start,conflict,chr_req,chr_cancel,chr_idle,chr_ready,chr_reply,chr_error;
 wire [7:0] write_data,chr_q,pixels;
 wire [17:0] chr_addr,chr_reply_addr; wire [15:0] chr_gen,chr_reply_gen;
 wire plan_ready,out_valid,done,fault;wire [4:0] pos;wire [5:0] len;
 wire [7:0] ram_bus=drive_data?write_data:8'hzz;
 assign #50 ram_bus=!oe_n?physical[ram_addr[12:0]]:8'hzz;
 time pulse_start;reg [26:0] wr_sample;
 always @(posedge clk)scan_data<=live[scan_addr];
 always @(negedge we_n)if(!reset)begin
  if(!oe_n||!drive_data||ram_addr[18:13]!=6'h3f)$fatal(1,"SRAM ownership");
  pulse_start=$time;wr_sample={ram_addr,write_data};
 end
 always @(posedge we_n)if(!reset && pulse_start!=0)begin
  if($time-pulse_start<40 || wr_sample!={ram_addr,write_data})$fatal(1,"SRAM write timing");
  physical[ram_addr[12:0]]=write_data;
 end
 nes_chr_snapshot snap(.clk(clk),.reset(reset||stop),.changed(changed),.start(start),.collecting(collecting),
`ifdef FF3_PAGES
  .changed_page(changed_page),
`endif
  .discard(discard),.retire(retire),.start_gen(gen),.retire_gen(retire_gen),.can_start(can_start),.conflict(conflict),
  .scan_addr(scan_addr),.scan_data(scan_data),.read_req(chr_req),.cancel(chr_cancel),.read_addr(chr_addr),
  .read_gen(chr_gen),.ready(chr_ready),.idle(chr_idle),.response(chr_reply),.error(chr_error),.data(chr_q),
  .reply_addr(chr_reply_addr),.reply_gen(chr_reply_gen),.ram_addr(ram_addr),.oe_n(oe_n),.we_n(we_n),
  .drive_data(drive_data),.write_data(write_data),.ram_q(ram_bus));
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) dut(.clk(clk),.reset(reset),.stop(stop),.frame_owned(owned),.geometry_valid(owned),
  .frame_generation(gen),.source_ready(1'b1),.source_is_rom(1'b0),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1),
  .plan_valid(plan_valid),.plan_short(1'b1),.plan_ready(plan_ready),.plan_kind(kind),.plan_generation(gen),.plan_slot(10'd1),
  .plan_tag(tag),.plan_rows(48'hff6b646d2240),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(112'd0),
  .chr_req(chr_req),.chr_cancel(chr_cancel),.chr_addr(chr_addr),.chr_gen(chr_gen),.chr_ready(chr_ready),.chr_idle(chr_idle),
  .chr_reply(chr_reply),.chr_error(chr_error),.chr_q(chr_q),.chr_reply_addr(chr_reply_addr),.chr_reply_gen(chr_reply_gen),
  .out_ready(1'b1),.out_valid(out_valid),.out_index(pos),.out_length(len),.out_data(pixels),.fault(fault),.done(done));
 task freeze_copy;
  wait(can_start);@(negedge clk);start=1;collecting=1;
  for(int i=0;i<8192;i++)if(physical[i]!==live[i])$fatal(1,"snapshot byte %d",i);
  for(int i=0;i<16;i++)expected[i]=live[tag*16+i];
  @(negedge clk);start=0;
 endtask
 task send(input bit obj);
  integer count;integer off;
  @(negedge clk);kind=obj;plan_valid=1;
  do @(posedge clk);while(!plan_ready);
  @(negedge clk);plan_valid=0;count=0;
  while(!done)begin
   @(posedge clk);
   if(fault)$fatal(1,"producer fault");
   if(out_valid)begin
    off=(pos[0]?8:0)+((48'hff6b646d2240>>(3*pos[3:0]))&7);
    if(pos!=count || pixels!==(pos>=16?8'd0:expected[off]) || len!=(obj?32:16))$fatal(1,"tile byte %d",count);
    count++;
   end
  end
  if(count!=(obj?32:16))$fatal(1,"missing bytes");
 endtask
 initial begin
  for(int i=0;i<8192;i++)live[i]=(i^(i>>7))&255;
  $readmemh("transition.hex",fixture);tag=fixture[0];source_frame=fixture[1];
  if($isunknown(tag) || tag>=512 || source_frame<2)$fatal(1,"missing FF3 fixture");
  for(int i=0;i<16;i++)live[tag*16+i]=fixture[2+i];
  repeat(4)@(negedge clk);reset=0;
`ifdef FF3_PAGES
  // Dirty an already copied byte while its page is in flight. Dirty a
  // second page while the first is being revisited, then verify all 8 KiB.
  wait(scan_addr==20);@(negedge clk);changed=1;changed_page=0;live[2]^=8'h55;
  @(negedge clk);changed=0;
  wait(scan_addr==8191);wait(scan_addr==20);@(negedge clk);
  changed=1;changed_page=6;live[6200]^=8'hbb;
  @(negedge clk);changed=0;
`endif
  freeze_copy();
  @(negedge clk);collecting=0;owned=1;changed=1;changed_page=tag[8:6];
  for(int i=0;i<16;i++)live[tag*16+i]=fixture[18+i];
  @(negedge clk);changed=0;
  send(0);send(1);
  @(negedge clk);retire_gen=gen-1;retire=1;
  @(negedge clk);if(can_start || !snap.held)$fatal(1,"stale retire accepted");
  retire_gen=gen;
  @(negedge clk);owned=0;retire=0;gen++;freeze_copy();
  @(negedge clk);owned=1;collecting=0;send(0);send(1);
  $display("FF3 ROM frame=%0d tile=%0d old and new BG/OBJ bytes match",source_frame,tag);
  @(negedge clk);retire_gen=gen;retire=1;
  @(negedge clk);retire=0;owned=0;gen++;freeze_copy();
  @(negedge clk);changed=1;changed_page=7;live[8176]^=8'h75;
  @(negedge clk);changed=0;if(!conflict)$fatal(1,"midframe write accepted");
  discard=1;collecting=0;
  @(negedge clk);discard=0;gen++;freeze_copy();collecting=0;owned=1;
  @(negedge clk);plan_valid=1;@(posedge clk);@(negedge clk);plan_valid=0;
  wait(!oe_n);@(negedge clk);stop=1;owned=0;
  @(negedge clk);if(chr_reply || !oe_n || !we_n || drive_data || out_valid)$fatal(1,"STOP");
  stop=0;gen++;freeze_copy();collecting=0;owned=1;send(0);
  $display("PASS FF3 8192B snapshot, BG/OBJ byte order, write during lease, discard, stale retire, STOP/cold");$finish;
 end
 initial begin repeat(400000)@(posedge clk);$fatal(1,"timeout");end
endmodule
