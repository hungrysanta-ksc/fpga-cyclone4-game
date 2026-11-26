// Test observation boundaries on the shipped 14-bit source and two-bank publisher.
// Group count, kind, slot offsets, final length and tokens are taken from MMC1025.
`timescale 1ps/1ps
module tb_nes_kirby1026;
 localparam GEN=16'd1619, SEED=32'd3129, LAST=SEED+6;
 reg nes=0,host=0,reset=1,stop=0;
 always #23281 nes=!nes;
 always #5952 host=!host;
 integer scenario,hold_cycles=800,cycle=0,hcycle=0;
 reg pv=0,finish=0,capture=0,seal_capture=0;
 reg [1:0] kind;
 reg [9:0] slot;
 reg [13:0] tag;
 wire ready,permit,tv,tr,done,capready,ender,fault,bulk_fault,chunk,writer,reader,returned_error;
 wire [7:0] td;
 wire [4:0] ti;
 wire [5:0] tl;
 wire [1:0] tk;
 wire [9:0] ts,chunk_slot;
 wire [15:0] tg,cg;
 wire [31:0] token;
 wire [11:0] length;
 wire ck;
 reg [21:0] back=0;
 wire [21:0] addr;
 wire req;
 reg [2:0] delay=0;
 function automatic [7:0] rom(input [21:0] a);
  return a[7:0]^a[15:8]^{6'd0,a[17:16]}^8'h97;
 endfunction
 integer index_tile=0,rom_wait=0,bank_wait=0,open_hold=0,last_reads=0;
 wire rom_block=scenario==1 && index_tile>=19 && rom_wait<hold_cycles;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) src(.clk(nes),.reset(reset),.stop(stop),
  .hint(1'b0),.hint_tag(14'd0),.hint_mask(8'd0),.page963(1'b0),.page_base963(11'd0),
  .cap_start(capture),.cap_seal(seal_capture),.cap_sample(1'b0),.cap_release(1'b0),
  .cap_generation(GEN),.cap_release_generation(GEN),.cap_address(18'd0),.cap_data(8'd0),.cap_ready(capready),
  .frame_owned(1'b1),.geometry_valid(1'b1),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),
  .captured_epoch(32'd1),.live_epoch(32'd1),.frame_generation(GEN),
  .plan_short(1'b1),.plan_valid(pv&&permit),.plan_ready(ready),.plan_kind(kind),.plan_tag(tag),
  .plan_slot(slot),.plan_generation(GEN),.plan_mask(kind==2?8'd0:8'hff),.plan_alt_mask(8'd0),
  .plan_alt_tags(112'd0),.plan_rows(kind==2?48'd0:48'hff6b646d2240),
  .core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),.qualified_slot(!rom_block),
  .mem_ready(delay==0),.mem_response(delay==1),.mem_error(1'b0),.mem_response_address(back),
  .mem_data(rom(back)),.bg_word(rom(back|22'd8)),.mem_request(req),.mem_address(addr),
  .out_valid(tv),.out_ready(tr),.out_index(ti),.out_data(td),.out_kind(tk),.out_length(tl),
  .out_slot(ts),.out_generation(tg),.done(done),.fault(fault));
 wire bank_block=scenario==2 && token==SEED+4 && open_hold<hold_cycles;
 reg [63:0] published=0,visible=0,observed=0,last_done=0,end_sent=0,prior_return=0;
 wire defer_poll=scenario==4 && token==LAST && (!visible || hcycle-visible<hold_cycles);
 wire consume=chunk && !bank_block && !defer_poll;
 nes_tile_bulk206 bulk(.nes_clk(nes),.host_clk(host),.active(1'b1),.reset(reset),.stop(stop),.source_fault(fault),
  .plan_valid(pv),.plan_taken(pv&&permit&&ready),.plan_kind(kind),.plan_slot(slot),.plan_generation(GEN),.plan_permit(permit),
  .tile_valid(tv),.tile_ready(tr),.tile_data(td),.tile_index(ti),.tile_length(tl),.tile_kind(tk),.tile_slot(ts),.tile_generation(tg),
  .end_valid(finish),.end_ready(ender),.end_generation(GEN),.token_seed(SEED),
  .writer903(writer),.reader903(reader),.chunk_ready(chunk),.chunk_length(length),.chunk_kind(ck),
  .chunk_slot(chunk_slot),.chunk_generation(cg),.chunk_token(token),.consume(consume),.consume_token(token),
  .consume_error(returned_error),.address(24'd0),.read_n(1'b1),.write_n(1'b1),.fault(bulk_fault));
 integer units[0:6]='{1,3,1,2,7,5,3};
 integer starts[0:6]='{0,654,0,2,5,19,12};
 integer g,j,nreturn=0,nbyte=0;
 reg [7:0] emitted[0:639];
 integer ncheck=0,k;
 always @(posedge nes)begin
  cycle++;
  if(delay!=0)delay<=delay-1'b1;
  if(req)begin back<=addr;delay<=4;end
  if(index_tile>=19 && src.ahead.foreground && !src.shared_ready)rom_wait++;
  if(index_tile>=19 && src.ahead.foreground && src.shared_ready) last_reads++;
  if(tv&&tr)begin
   if(tg!==GEN || $isunknown(td))$fatal(1,"invalid tile byte");
   emitted[nbyte]=td;nbyte++;
  end
  if(finish && ender)end_sent=hcycle;
  if(done && index_tile==21)last_done=hcycle;
 end
 always @(posedge host)begin
  hcycle++;
  if(!reset&&!stop&&(fault||bulk_fault||returned_error))$fatal(1,"producer fault");
  if(bulk.state==bulk.OPEN && !bulk.begin_ready)begin bank_wait++;if(bank_block)open_hold++;end
  if(bulk.state==bulk.SEAL && bulk.token==LAST)published=hcycle;
  if(chunk && token==LAST && !visible)visible=hcycle;
  if(consume)begin
   if(token!==SEED+nreturn || cg!==GEN || ck!==(nreturn>=2) || chunk_slot!==starts[nreturn] ||
      length!==units[nreturn]*(ck?32:16))$fatal(1,"wrong descriptor %d",nreturn);
   for(k=0;k<length;k++)begin
    if(bulk.aperture.storage[reader*2048+k]!==emitted[ncheck])$fatal(1,"bank byte %d",ncheck);
    ncheck++;
   end
   if(token==LAST-1)prior_return=hcycle;
   if(token==LAST)observed=hcycle;
   nreturn++;
  end
 end
 task n;@(negedge nes);endtask
`ifdef KIRBY1027_OBSERVER
 `include "kirby1027_scoreboard.svh"
`endif
 initial begin
  if(!$value$plusargs("CASE=%d",scenario))$fatal;
`ifdef KIRBY1027_OBSERVER
  hold_cycles=45000;
`endif
  repeat(8)n;reset=0;while(!capready)n;capture=1;n;capture=0;n;seal_capture=1;n;seal_capture=0;
  repeat(40)n;
  for(g=0;g<7;g++)for(j=0;j<units[g];j++)begin
   kind=g==0?2:(g==1?0:1);slot=starts[g]+j;tag=g==0?0:14'h2180+index_tile;
   pv=1;do @(posedge nes); while(!(ready&&permit));n;pv=0;
   while(!done)n;n;index_tile++;
  end
  if(scenario==3)repeat(hold_cycles)n;
  while(!ender)n;finish=1;n;finish=0;
  while(nreturn!=7)n;
`ifdef KIRBY1027_OBSERVER
  inspect_header();
`endif
  // Flush/abort cannot expose an old chunk as ready after the reset releases.
  stop=1;repeat(8)n;stop=0;repeat(12)n;
`ifdef KIRBY1027_OBSERVER
  if(trace.complete || trace.read_ok || trace.reply!==0)$fatal(1,"STOP left a readable footer");
`endif
  if(chunk||req||tv||nbyte!=640||ncheck!=640||!last_reads||
     !(last_done<end_sent && end_sent<=published && published<=visible && visible<=observed))$fatal(1,"end state");
  $display("PASS1026 case=%0d fg_wait_nes=%0d bank_wait_host=%0d final_grants=%0d prior_return=%0d last_done=%0d end=%0d publish=%0d visible=%0d poll=%0d bytes=%0d",
   scenario,rom_wait,bank_wait,last_reads,prior_return,last_done,end_sent,published,visible,observed,ncheck);
  $finish;
 end
 initial #(64'd5000000000) $fatal(1,"timeout group=%d tile=%d ownership=%d",g,index_tile,nreturn);
endmodule
