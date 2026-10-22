# SPDX-License-Identifier: MIT
"""Retain real E8/E9 decoder, tile/cache/priority arbiter and physical reader.

The integration uses recorded C plans and ROM bytes. Core requests and qualified
slot timing in the test are declared stress inputs, not a live NES CPU workload.
"""
from pathlib import Path
import shutil
from nes_delta231 import BASE,ROOT,sha,once

MODULE=r'''
module nes_plan_rom267(
 input wire clk,host_clk,mem_clk,reset,stop,lease,retire_permitted,
 input wire [15:0] generation,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 input wire tile_closed,output wire tv,input wire tr,output wire [7:0] td,
 output wire [4:0] ti,output wire [5:0] tl,output wire [1:0] tk,output wire [9:0] ts,
 output wire ev,input wire er,
 input wire qualified,core_safe,core_request,input wire [21:0] core_address,
 output wire core_ready,core_response,output wire [7:0] core_data,
 output wire [21:0] psram_address,output wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,
 input wire [15:0] psram_data,output wire fault,drained,retire_done
);
 wire pw,pr,seal,idle,retire,done,ef,bf,sf,pv,pready,tdone;
 wire [7:0] pd,mask,am;wire [9:0] plen,slot;wire [4:0] pcount;
 wire [15:0] crc,pg,eg,tg;wire [1:0] kind;wire [12:0] tag;wire [47:0] rows;wire [103:0] tags;
 reg closed_q;always @(posedge host_clk)if(reset||stop)closed_q<=0;else closed_q<=tile_closed;
 nes_plan_spi200 endpoint(.clk(host_clk),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(sf||bf),
  .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.selected(selected),.miso(miso),.fault(ef),
  .plan_idle(idle),.plan_ready(pr),.plan_write(pw),.plan_data(pd),.plan_seal(seal),.plan_length(plen),.plan_plans(pcount),.plan_crc(crc),
  .retire_done(retire_done),.retire(retire),.end_generation(generation),
  .chunk_ready(1'b0),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),.chunk_generation(16'd0),.chunk_token(32'd0),
  .end_sealed(tile_closed&&!closed_q));
 nes_plan_batch206 transport(.host_clk(host_clk),.nes_clk(clk),.reset(reset),.active(1'b1),.stop(stop),.source_fault(ef||sf),
  .write_valid(pw),.write_ready(pr),.write_data(pd),.retire(retire),.retire_done(retire_done),.retire_permitted(retire_permitted),.retire_commit(),
  .seal(seal),.seal_length(plen),.seal_plans(pcount),.seal_crc(crc),.host_idle(idle),.fault(bf),.lease_valid(lease),.lease_generation(generation),
  .plan_valid(pv),.plan_ready(pready),.tile_done(tdone),.plan_kind(kind),.plan_generation(pg),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),
  .plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(tags),.end_valid(ev),.end_ready(er),.end_generation(eg));
 wire mr,mready,mresponse,merror;wire [21:0] ma,mra,cra;wire [7:0] md;wire ce;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) source(.clk(clk),.reset(reset),.stop(stop),.frame_owned(lease),.geometry_valid(lease),.frame_generation(generation),
  .source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1),
  .plan_valid(pv),.plan_ready(pready),.plan_kind(kind),.plan_generation(pg),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(tags),
  .qualified_slot(qualified),.core_safe(core_safe),.core_request(core_request),.core_address(core_address),.core_ready(core_ready),.core_response(core_response),.core_error(ce),.core_response_address(cra),.core_data(core_data),
  .mem_ready(mready),.mem_response(mresponse),.mem_error(merror),.mem_response_address(mra),.mem_data(md),.mem_request(mr),.mem_address(ma),
  .out_valid(tv),.out_ready(tr),.out_data(td),.out_index(ti),.out_length(tl),.out_kind(tk),.out_slot(ts),.out_generation(tg),.busy(),.done(tdone),.fault(sf),.drained(drained));
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem_clk),.reset(reset),.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),
  .check_ready(),.check_response(),.check_response_address(),.check_data(),.rom_request(mr),.rom_address(ma),.rom_ready(mready),.rom_response(mresponse),.rom_error(merror),.rom_response_address(mra),.rom_data(md),
  .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 assign fault=ef||bf||sf||ce;
endmodule
'''

TB=r'''
 parameter integer ROM_WINDOW=0;
 reg mem_clk267=0;always #2.976190476 mem_clk267=~mem_clk267;
 integer romcycle267=0,tile_at267=0,core_reads267=0,rom_reads267=0,denied267=0;
 integer tile_wait267=0,slot_wait267=0,core_block267=0;
 wire core_ready267,core_response267;wire [7:0] core_data267;
 wire qualify267=ROM_WINDOW==0 ? 1'b1 : (romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3);
 wire core_req267=active263&&core_ready267&&romcycle267%120==3;
 wire plan_selected267,plan_miso267,romfault267,romdrained267,plan_retired267;
 wire [21:0] psaddr267;wire ce1,ce2,oe267,we267,bhe267,ble267;wire [15:0] psdata267;
 reg [7:0] chr267[0:131071];initial $readmemh("chr.hex",chr267);
 function automatic [7:0] romvalue267(input [23:0] a);
  if(a>=24'h200000&&a<24'h220000)return chr267[a-24'h200000];else return a[7:0]^a[15:8]^a[23:16];
 endfunction
 wire [23:0] byteaddr267={psaddr267,ce1,1'b0};
 assign #70 psdata267=(!ce1 ^ !ce2)&&!oe267&&we267?{bhe267?8'hzz:romvalue267(byteaddr267),ble267?8'hzz:romvalue267(byteaddr267+1)}:16'hzzzz;
 nes_plan_rom267 planrom(.clk(clk),.host_clk(host_clk),.mem_clk(mem_clk267),.reset(reset),.stop(test_abort),
  .lease(waiting_display||flow_retired),.retire_permitted(flow_retired),.generation(generation),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(plan_selected267),.miso(plan_miso267),.tile_closed(dut.flow.tiles_closed),
  .tv(tv263),.tr(tr263),.td(td263),.ti(ti263),.tl(tl263),.tk(tk263),.ts(ts263),.ev(ev),.er(er),
  .qualified(qualify267),.core_safe(1'b1),.core_request(core_req267),.core_address(22'h001234),.core_ready(core_ready267),.core_response(core_response267),.core_data(core_data267),
  .psram_address(psaddr267),.psram_1ce(ce1),.psram_2ce(ce2),.psram_oe(oe267),.psram_we(we267),.psram_bhe(bhe267),.psram_ble(ble267),.psram_data(psdata267),
  .fault(romfault267),.drained(romdrained267),.retire_done(plan_retired267));
 assign selected=main_selected267||plan_selected267;
 assign miso=plan_selected267?plan_miso267:main_miso267;
 always @(posedge clk)if(!reset)begin
  romcycle267++;
  if(romfault267)$fatal(1,"plan/ROM fault e%0d b%0d s%0d",planrom.ef,planrom.bf,planrom.sf);
  if(main_selected267&&plan_selected267)$fatal(1,"plan/output SPI collision");
  if(core_response267)begin if(core_data267!==8'h26)$fatal(1,"core priority data");core_reads267++;end
  if(planrom.mr&&planrom.mready&&!core_req267)rom_reads267++;
  if(planrom.source.arb_request&&!planrom.source.arb_ready)denied267++;
  // back_request is ready-gated by the cache, so the legacy denied counter is
  // not a contention measure. Observe the upstream unaccepted tile request.
  if(planrom.source.tile_request&&!planrom.source.tile_ready)begin
   tile_wait267++;
   if(!qualify267)slot_wait267++;
   if(qualify267&&core_req267&&planrom.source.cache_path.cache.live&&
      !planrom.source.cache_path.cache.pending&&!planrom.source.cache_path.cache.hit_reply&&
      !planrom.source.cache_path.cache.hit)begin
    core_block267++;
    if(!planrom.mr||planrom.ma!==22'h001234||planrom.source.arb_request)$fatal(1,"core priority while fill waits");
   end
  end
  if(tv263&&tr263)begin
   if(td263!==tiles263[tile_at267])$fatal(1,"actual ROM tile byte frame%0d byte%0d got%h expected%h",f,tile_at267,td263,tiles263[tile_at267]);
   tile_at267++;
  end
 end
'''

def bind(d,s,src,pins,plans):
 board=BASE/'probes/nes-source240/board01'
 for n in ['nes_plan_spi200.sv','nes_plan_batch206.sv','nes_source_tile192.sv','nes_tile205.sv','nes_chr_cache192.sv','nes_native_arbiter165.sv','nes_rom_physical.sv']:
  p=board/n;shutil.copyfile(p,d/n);src[n]='';pins[p.relative_to(BASE).as_posix()]=sha(p)
 (d/'nes_plan_rom267.sv').write_text(MODULE,encoding='utf-8',newline='\n');src['nes_plan_rom267.sv']=''
 shutil.copyfile(plans/'chr.hex',d/'chr.hex')
 s=once(s,'reg tv263=0;wire tr263;reg [7:0] td263=0;','wire tv263;wire tr263;wire [7:0] td263;')
 s=once(s,'reg [4:0] ti263=0;reg [5:0] tl263=16;reg [1:0] tk263=0;reg [9:0] ts263=0;', 'wire [4:0] ti263;wire [5:0] tl263;wire [1:0] tk263;wire [9:0] ts263;')
 s=once(s,'reg idvalid=0,ev=0;wire er;', 'reg idvalid=0;wire ev,er;')
 s=once(s,'wire start_ready,source_done,selected,miso;', 'wire start_ready,source_done,selected,miso,main_selected267,main_miso267;')
 s=once(s,'.selected(selected),.miso(miso),.done(source_done)', '.selected(main_selected267),.miso(main_miso267),.done(source_done)')
 a=s.index(' task tiles_task263;');b=s.index(' initial begin : bus263',a)
 s=s[:a]+''' task tiles_task263;begin
  wait(ev&&er);@(negedge clk);wait(!ev);
  if(tile_at267!=tile_sizes263[1])$fatal(1,"actual ROM tile count");
  $fwrite(events261,"rom267,%0d,%0d,%0d,%0d,%0d\\n",f,tile_at267,core_reads267,rom_reads267,denied267);
  $fwrite(events261,"romwait267,%0d,%0d,%0d,%0d\\n",f,tile_wait267,slot_wait267,core_block267);
  if(ROM_WINDOW==1&&core_block267==0)$fatal(1,"qualified test did not exercise core priority");
 end endtask
'''+s[b:]
 s=once(s,'  active263=1;producer_done263=0;', '  tile_at267=0;active263=1;producer_done263=0;')
 s=once(s,' task clear_output;',TB+'\n task clear_output;')
 return s
