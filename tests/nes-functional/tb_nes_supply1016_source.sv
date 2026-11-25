`timescale 1ns/1ps
module tb_nes_supply1016_source;
 reg clk=0;always #10 clk=!clk;
 reg host=0;always #3 host=!host;
 reg reset=1,stop=0,capture=0,sample=0,seal=0,origin=0,pv=0;
 reg [12:0] tag=13'h1801;reg [9:0] slot=1;reg [16:0] capaddr;
 wire ready,cap_ready,sample_ready,req,done,valid,fault,drained;
 wire [21:0] addr;reg [21:0] back;reg [5:0] delay=0;
 wire [7:0] outbyte;wire [4:0] idx;reg [7:0] count=0;
 function automatic [7:0] value(input [16:0] a);return a[7:0]^a[15:8]^8'h97;endfunction
 reg [8:0] rd=0;wire [31:0] q;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) dut(.clk(clk),.host1016(host),.rd1016(rd),.bw1016(1'b0),.word1016(32'd0),.q1016(q),
 .origin1016(origin),.reset(reset),.stop(stop),.hint(1'b0),.hint_tag(13'd0),.hint_mask(8'd0),
 .page963(1'b0),.page_base963(10'd0),.cap_start(capture),.cap_sample(sample),.cap_seal(seal),
 .cap_release(1'b0),.cap_generation(16'd1384),.cap_release_generation(16'd1384),
 .cap_address(capaddr),.cap_data(value(capaddr)),.cap_ready(cap_ready),.cap_sample_ready(sample_ready),
 .frame_owned(1'b1),.geometry_valid(1'b1),.frame_generation(16'd1384),.source_ready(1'b1),
 .source_is_rom(1'b1),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1),
 .plan_short(1'b1),.plan_kind(2'd1),.plan_generation(16'd1384),.plan_tag(tag),.plan_slot(slot),
 .plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),.plan_rows(48'hff6b646d2240),
 .plan_valid(pv),.plan_ready(ready),.core_request(1'b0),.core_address(22'd0),.core_safe(1'b1),
 .qualified_slot(count[4:0]==0),.mem_ready(delay==0),.mem_response(delay==1),.mem_error(1'b0),
 .mem_response_address(back),.mem_data(value(back[16:0])),.bg_word(value(back[16:0]|17'd8)),
 .mem_request(req),.mem_address(addr),.out_ready(1'b1),.out_valid(valid),.out_index(idx),
 .out_data(outbyte),.done(done),.fault(fault),.drained(drained));
 integer physical=0,emitted=0,ncapture=0,nrow=0,nrom=0;
 reg [2:0] sr;
 always @(posedge clk)begin
  count<=count+1'b1;
  if(delay!=0)delay<=delay-1'b1;
  if(req)begin physical++;delay<=4;back<=addr;end
  if(fault)$fatal(1,"source fault");
  if(valid)begin
   sr=48'hff6b646d2240>>(idx[3:0]*3);
   if(outbyte!==(idx>=16?8'd0:value({tag,idx[0],sr})))$fatal(1,"tile data");
   emitted++;
  end
 end
 task n;@(negedge clk);endtask
 integer t,a,fd;
 initial begin
  repeat(7)n;reset=0;while(!cap_ready)n;capture=1;n;capture=0;
  for(a=0;a<16;a++)begin
   while(!sample_ready)n;capaddr=17'h18010+a;sample=1;n;sample=0;repeat(3)n;
  end
  seal=1;n;seal=0;repeat(256)n;origin=1;repeat(6)n;
  for(t=0;t<15;t++)begin
   slot=t+1;tag=t==0?13'h1801:13'h1802+(t-1)/2;
   while(!ready)n;pv=1;n;pv=0;while(!done)n;n;
  end
  repeat(4)n;
  if(emitted!=480||!physical||dut.capture1016.bad)$fatal(1,"incomplete source");
  fd=$fopen("source-words.hex","w");
  for(a=0;a<=dut.capture1016.cursor;a++)begin
   rd=a;repeat(2)@(negedge host);$fdisplay(fd,"%08x",q);
  end
  $fclose(fd);
  stop=1;n;repeat(3)n;if(valid||req)$fatal(1,"late output after STOP");
  $display("PASS1016 verified 480 emitted bytes through actual capture cache, row cache and ROM, grants=%0d",physical);
  $finish;
 end
 initial #50000000 $fatal(1,"source timeout");
endmodule
