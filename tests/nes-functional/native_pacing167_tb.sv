// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Actual fill + arbiter + exporter, conditional NES slots and a paced host.
// Query/PSRAM/host are models, not an SMB3/core or physical timing replay.
module native_pacing167_tb;
 parameter POLICY=2, GAP=1900, PHASE=0, MODE=0, TILES=15;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,owned=1;reg [15:0] generation=12;
 integer ticks=0,received=0,aborts=0,commits=0,begins=0,ends=0,first_fill=0;
 integer grants=0,core_grants=0,age=0;reg pending=0;
 wire [31:0] cyc;wire [9:0] tile_count;wire [13:0] byte_count;
 wire q,fq;wire [2:0] qk,fqk;wire [12:0] qi,fqi;wire [15:0] qg,fqg;
 reg qr=0,fr=0;reg [63:0] fd=0;
 wire start,fb,done,success,quarantine,release_frame,eb,ack_ready;
 wire [3:0] fe,ee;wire bv,br;wire [7:0] bd;wire [12:0] bt;wire [3:0] bl;wire [1:0] bk;wire [15:0] bg;
 wire req,abort_mem,ready,idle,response,err;wire [21:0] addr,respaddr;wire [15:0] mg,rg;wire [7:0] md;
 wire mreq;wire [21:0] ma;reg mr=0;reg [21:0] mra=0,saved=0;reg [7:0] mdata=0;
 wire fault,cr,cp,ce;wire [21:0] ca;wire [7:0] cd;
 wire [95:0] tx;wire valid;reg ack=0;
 wire consume=MODE!=2 && ticks%GAP==0;
 wire slot=MODE!=1 && (ticks+PHASE)%357368>=330088 && (ticks+PHASE)%357368<354640 && ticks%12==3;
 wire core_request=ticks%97==3 && !pending && !mr;
 nes_native_fill165 #(.COOPERATIVE_WAIT(POLICY!=0),.WAIT_CYCLES(131072),.MAX_CYCLES(POLICY==2?16777216:2097152)) fill(
 .clk(clk),.reset(reset),.start(start),.clear(release_frame),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(generation),
 .query(fq),.query_kind(fqk),.query_index(fqi),.query_generation(fqg),.response(fr),.hit(1'b1),.data(fd),
 .mem_idle(idle),.mem_ready(ready),.mem_response(response),.mem_error(err),.mem_response_address(respaddr),.mem_response_generation(rg),.mem_data(md),
 .mem_request(req),.mem_abort(abort_mem),.mem_address(addr),.mem_generation(mg),
 .byte_valid(bv),.byte_ready(br),.byte_data(bd),.byte_tile(bt),.byte_lane(bl),.byte_kind(bk),.byte_generation(bg),
 .busy(fb),.done(done),.quarantine(quarantine),.success(success),.error(fe),.tile_count(tile_count),.byte_count(byte_count),.cycles(cyc));
 nes_native_arbiter165 arb(.clk(clk),.reset(reset),.slot(slot),.core_safe(1'b1),
 .core_request(core_request),.core_address(22'd123),.core_ready(cr),.core_response(cp),.core_error(ce),.core_response_address(ca),.core_data(cd),
 .fill_request(req),.fill_abort(abort_mem),.fill_address(addr),.fill_generation(mg),.fill_ready(ready),.fill_idle(idle),.fill_response(response),.fill_error(err),.fill_response_address(respaddr),.fill_response_generation(rg),.fill_data(md),
 .mem_ready(!pending&&!mr),.mem_response(mr),.mem_error(1'b0),.mem_response_address(mra),.mem_data(mdata),.mem_request(mreq),.mem_address(ma),.fault(fault));
 nes_native_export165 #(.MAX_CYCLES(POLICY==2?33554432:4194304)) exp(
 .clk(clk),.reset(reset),.enable(1'b1),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(generation),
 .row_count(8'd224),.object_count(8'd2),.exception_count(8'd0),.group_count(6'd30),.palette_count(6'd1),
 .release_frame(release_frame),.query(q),.query_kind(qk),.query_index(qi),.query_generation(qg),.response(qr),.hit(1'b1),.data(64'd0),
 .fill_start(start),.fill_busy(fb),.fill_done(done),.fill_success(success),.fill_error(fe),
 .byte_valid(bv),.byte_ready(br),.byte_data(bd),.byte_tile(bt),.byte_lane(bl),.byte_kind(bk),.byte_generation(bg),
 .tx_valid(valid),.tx_ready(consume),.tx_data(tx),.ack_valid(ack),.ack_accept(1'b1),.ack_generation(generation),.ack_ready(ack_ready),.busy(eb),.error(ee));
 always @(posedge clk)begin
  ticks<=ticks+1;qr<=q;fr<=fq && MODE!=4;fd<=fqi<TILES?1:0;mr<=0;ack<=0;
  if(start && first_fill==0)first_fill<=ticks;
  if(release_frame)owned<=0;
  if(!reset && req && ready)begin
   if(core_request||!slot)$fatal(1,"fill violates priority/slot");grants<=grants+1;
  end
  if(!reset && core_request)begin
   if(!mreq||ma!=123)$fatal(1,"lost core priority");core_grants<=core_grants+1;
  end
  if(!reset && mreq && !pending && !mr)begin pending<=1;saved<=ma;age<=0;end
  if(pending)begin
   age<=age+1;
   if(age==(MODE==3 && saved!=123?20:2))begin
    pending<=0;mr<=1;mra<=saved;mdata<=saved[7:0]^8'h5a;
   end
  end
  if(!reset && bv && br)begin
   if(bd!==({bt[3:0],bl}^8'h5a)||bt*16+bl!=received||bg!=generation)$fatal(1,"wrong byte/order");
   received<=received+1;
  end
  if(!reset && valid && consume && tx[95:93]==7)case(tx[76:64])
   0:begins<=begins+1;
   1:begin ends<=ends+1;ack<=1;end
   2:begin
    if(tx[7:4]!==exp.fill_detail || tx[3:0]!==ee)$fatal(1,"ABORT detail stale");
    $display("ABORT reason=%0d fill=%0d received=%0d ticks=%0d",tx[3:0],tx[7:4],received,ticks);aborts<=aborts+1;
   end
   3:commits<=commits+1;
  endcase
 end
 initial begin
  repeat(4)@(negedge clk);reset=0;
  if(MODE==2)begin
   // Host never consumes even the header. Whole export bound must cancel.
   wait(ee!=0);if(ee!=1)$fatal(1,"host starvation not bounded");
  end else begin
   wait(commits+aborts!=0);@(negedge clk);
   if(MODE==0 && (POLICY==2 || GAP==20))begin
    if(commits!=1||aborts||received!=TILES*16||ends!=1||begins!=1||fault)$fatal(1,"completion");
   end else begin
    if(commits||aborts!=1)$fatal(1,"expected rejection");
    if(MODE==0 && POLICY==0 && (ee!=4||exp.fill_detail!=4))$fatal(1,"legacy wait expected");
    if(MODE==0 && POLICY==1 && ee!=1 && !(ee==4&&exp.fill_detail==3))$fatal(1,"total budget expected");
    if(MODE==1 && (ee!=4||exp.fill_detail!=3))$fatal(1,"grant starvation total");
    if(MODE==3 && (ee!=4||exp.fill_detail!=7||!fault))$fatal(1,"accepted-read fault");
    if(MODE==4 && (ee!=4||exp.fill_detail!=4))$fatal(1,"lookup short timeout");
   end
  end
  $display("PASS PACING167 policy=%0d gap=%0d phase=%0d mode=%0d tiles=%0d ticks=%0d fill_at=%0d bytes=%0d grants=%0d core=%0d",POLICY,GAP,PHASE,MODE,TILES,ticks,first_fill,received,grants,core_grants);$finish;
 end
 initial begin #400000000;$fatal(1,"test watchdog");end
endmodule
