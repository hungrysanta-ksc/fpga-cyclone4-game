// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Actual205 byte stream +193 unpublished RAM/mailbox/aperture.
// Memory and lease are fixtures. Fault delivery delayed two NES edges.
module tile_stream205_tb;
 reg clk=0,host_clk=0,reset=1,stop=0,lease=1,pv=0,credit=1;
 always #23.28 clk=!clk;always #5.952 host_clk=!host_clk;
 wire pr,req,cancel,ov,ready,busy,fault,done;wire [16:0] addr;
 wire [15:0] mg,og;wire [7:0] od;wire [4:0] oi;wire [5:0] olen;wire [1:0] ok;wire [9:0] os;
 reg response=0,error=0;reg [16:0] ra=0;reg [15:0] rg=0;reg [7:0] rd=0;
 reg [1:0] late_fault=0;reg [2:0] bad=0;
 wire chunk,bulk_fault;wire [11:0] clen;wire [31:0] token;wire [7:0] bd;wire bo,dir;
 reg ending=0;wire end_ready;integer count=0,checks=0,kind=0,prefix=0;reg check_partial=0;
 reg [7:0] held;reg [4:0] held_index;
 nes_tile205 #(.EXTERNAL_PLAN(1),.MAX_CYCLES(2000)) tile(
 .clk(clk),.reset(reset),.stop(stop),.lease_valid(lease),.lease_generation(16'd7),
 .plan_valid(pv),.plan_ready(pr),.plan_kind(2'd0),.plan_generation(16'd7),.plan_slot(10'd1),
 .plan_tag(13'd3),.plan_rows(48'hfac688fac688),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
 .mem_idle(1'b1),.mem_ready(1'b1),.mem_request(req),.mem_cancel(cancel),.mem_address(addr),.mem_generation(mg),
 .mem_response(response),.mem_error(error),.response_address(ra),.response_generation(rg),.response_data(rd),
 .out_valid(ov),.out_ready(ready&&credit),.out_data(od),.out_index(oi),.out_length(olen),.out_kind(ok),.out_slot(os),.out_generation(og),
 .busy(busy),.fault(fault),.done(done));
 nes_tile_bulk193 bulk(.nes_clk(clk),.host_clk(host_clk),.reset(reset),.active(1'b1),.stop(stop),.source_fault(late_fault[1]),
 .tile_valid(ov&&credit),.tile_ready(ready),.tile_data(od),.tile_index(oi),.tile_length(olen),.tile_kind(ok),.tile_slot(os),.tile_generation(og),
 .end_valid(ending),.end_ready(end_ready),.end_generation(16'd7),.token_seed(32'd1),
 .chunk_ready(chunk),.chunk_length(clen),.chunk_token(token),.chunk_kind(),.chunk_slot(),.chunk_generation(),
 .consume(1'b0),.consume_token(32'd0),.consume_error(),.address(24'h400800),.read_n(1'b1),.write_n(1'b1),
 .data_out(bd),.oe_n(bo),.dir(dir),.fault(bulk_fault),.end_sealed(),.sealed_generation());
 always @(posedge clk)begin
  if(reset)begin response<=0;late_fault<=0;count<=0;end
  else begin
   late_fault<={late_fault[0],fault};response<=req;
   if(req)begin ra<=addr^(bad==2?17'd1:17'd0);rg<=mg^(bad==3?16'd1:16'd0);rd<=addr[7:0]^8'h5a;error<=bad==1;end
   if(ov&&ready&&credit)count<=count+1;
  end
 end
 always @(posedge host_clk)if(check_partial&&!reset&&(chunk||bulk.word_valid))$fatal(1,"partial tile published");
 task tick;begin @(posedge clk);#1;end endtask
 task fresh;
  begin @(negedge clk);reset=1;stop=0;lease=1;pv=0;credit=1;bad=0;ending=0;check_partial=0;
   repeat(4)tick();@(negedge clk);reset=0;repeat(8)tick();end
 endtask
 task submit;
  begin while(!pr)tick();@(negedge clk);pv=1;tick();@(negedge clk);pv=0;end
 endtask
 initial begin
  for(kind=0;kind<7;kind++)for(integer k=0;k<3;k++)begin
   prefix=k==0?1:k==1?7:15;fresh();check_partial=1;submit();
   wait(count==prefix);@(negedge clk);credit=0;
   if(kind==0)lease=0;
   if(kind>=1&&kind<=3)bad=3'(kind);
   if(kind==4)begin wait(ov);@(negedge clk);tile.cycles=2000;end
   if(kind==5)stop=1;
   if(kind==6)reset=1;
   if(kind<4)begin repeat(3)tick();end
   repeat(15)tick();
   if(kind<5&&!fault)$fatal(1,"missing failure kind=%0d prefix=%0d",kind,prefix);
   if(ov||chunk||bulk.word_valid)$fatal(1,"failed tile still visible");checks++;
  end
  // A stalled byte stays stable; after recovery a complete tile alone is exposed.
  fresh();submit();wait(ov);@(negedge clk);credit=0;held=od;held_index=oi;
  repeat(13)begin tick();if(!ov||od!==held||oi!==held_index)$fatal(1,"stalled byte changed");end
  @(negedge clk);credit=1;wait(done);tick();
  while(!end_ready)tick();@(negedge clk);ending=1;tick();@(negedge clk);ending=0;
  wait(chunk);if(clen!=16||token!=1||count!=16||fault||bulk_fault)$fatal(1,"recovery completion failed");checks++;
  $display("PASS STREAM205 checks=%0d",checks);$finish;
 end
 initial begin #500000;$fatal(1,"watchdog");end
endmodule
