# SPDX-License-Identifier: MIT
"""Real hint/cache/tile ownership: cancel unissued reads, drain accepted replies."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
from probe_nes_refill267 import run
TB=r'''`timescale 1ns/1ps
module handoff371_tb;
 reg h=0,n=0;always #5.952380952 h=~h;always #22.727272727 n=~n;
 reg reset=1,stop=0,pre=1,lease=0,qualified=0,pv=0;
 reg [113:0] link=0;wire active,hr,ready,response,error,hfault,hbusy,finished;
 wire [21:0] ha;wire pr,tv,done,fault,drained;wire [7:0] td;wire [4:0] ti;
 wire [5:0] tl;wire [1:0] tk;wire [9:0] ts;wire [15:0] tg;
 reg [1:0] pk=2;reg [9:0] ps=0;reg [12:0] pt=0;reg [47:0] rows=0;reg [7:0] mask=0;
 wire mr,mready;wire [21:0] ma;reg mresp=0,pending=0;reg [2:0] delayq=0;
 reg [21:0] held=0,mra=0;reg [7:0] md=0;integer reads=0,outs=0,finishes=0,cases=0;
 function automatic [7:0] value(input [21:0] a);return a[7:0]^a[15:8]^{2'd0,a[21:16]};endfunction
 assign mready=!pending&&!mresp;
 always @(posedge n)begin
  if(reset)begin pending<=0;mresp<=0;reads<=0;end
  else begin
   mresp<=0;
   if(pending)begin if(delayq==0)begin pending<=0;mresp<=1;mra<=held;md<=value(held);end else delayq<=delayq-1'b1;end
   if(mr)begin if(!mready)$fatal(1,"physical ownership collision");pending<=1;delayq<=2;held<=ma;reads++;end
  end
 end
 nes_hint361 #(.ALLOW_YIELD371(1)) hint(.yield371(lease&&pv),.host_clk(h),.clk(n),.reset(reset),.stop(stop),.prelease(pre),.display_lease(lease),.immutable(1'b1),
  .generation(16'd3),.epoch(32'd1),.serial(32'd3),.link(link),.active(active),.request(hr),.address(ha),.ready(ready),.response(response),.error(error),.fault(hfault),.busy(hbusy),.finished(finished));
 nes_source_tile192 #(.EXTERNAL_PLAN(1),.YIELD371(1)) source(.clk(n),.reset(reset),.stop(stop),.frame_owned(lease),.geometry_valid(lease),.frame_generation(16'd3),
  .source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1),
  .hint_active361(active),.hint_request361(hr),.hint_owner361(pre),.hint_address361(ha),.hint_ready361(ready),.hint_response361(response),.hint_error361(error),
  .plan_valid(pv),.plan_ready(pr),.plan_kind(pk),.plan_generation(16'd3),.plan_slot(ps),.plan_tag(pt),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
  .qualified_slot(qualified),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),
  .core_ready(),.core_response(),.core_error(),.core_response_address(),.core_data(),
  .mem_ready(mready),.mem_response(mresp),.mem_error(1'b0),.mem_response_address(mra),.mem_data(md),.mem_request(mr),.mem_address(ma),
  .out_valid(tv),.out_ready(1'b1),.out_data(td),.out_index(ti),.out_length(tl),.out_kind(tk),.out_slot(ts),.out_generation(tg),.busy(),.done(done),.fault(fault),.drained(drained));
 always @(posedge n)if(!reset)begin
  if(finished)finishes++;
  if(source.tile_response&&tk==2)$fatal(1,"hint reply routed to zero tile");
  if(tv)begin
   if(tg!=3||tl!=16||ti!=(outs%16))$fatal(1,"output identity");
   if(tk==2)begin if(td!=0||ts!=0)$fatal(1,"zero output");end
   else if(tk!=0||ts!=1||td!==value(22'h200000+22'h1240+(ti[0]?8:0)+(ti>>1)))$fatal(1,"BG response provenance kind%0d slot%0d index%0d actual%02x expected%02x addr%06x",tk,ts,ti,td,value(22'h200000+22'h1240+(ti[0]?8:0)+(ti>>1)),source.reply_address);
   outs++;
  end
 end
 task byte_link(input integer count,input [7:0] b);begin
  @(negedge h);link[110]=1;link[32:25]=8'hea;link[24:17]=b;link[16:7]=10'(count);
  @(negedge h);link[110]=0;
 end endtask
 task setup(input bit allow_rom);begin
  reset=1;stop=0;lease=0;pv=0;pre=1;link=0;qualified=allow_rom;pk=2;ps=0;pt=0;rows=0;mask=0;
  #1000;reset=0;#1000;outs=0;finishes=0;
  for(integer i=0;i<28;i++)begin
   case(i)0:byte_link(i,8'hea);1:byte_link(i,7);2:byte_link(i,3);4:byte_link(i,1);8:byte_link(i,3);
    default:byte_link(i,(i>=12&&i<26)?(i[0]?8'h01:8'h23):8'd0);endcase
  end
  @(negedge h);link[109]=1;link[108]=1;link[16:7]=28;@(negedge h);link[109]=0;
 end endtask
 task sendplan;begin
  @(negedge n);lease=1;pv=1;
  while(!pr)@(negedge n);
  @(negedge n);pv=0;
 end endtask
 initial begin
  for(integer stage=1;stage<=5;stage++)begin
   setup(stage!=3);
   wait(source.cache_path.cache.state==stage);sendplan();wait(done);@(negedge n);
   if(outs!=16||finishes||hfault||fault||active)$fatal(1,"handoff stage%0d outs%0d",stage,outs);
   if(stage==3&&reads!=0)$fatal(1,"unqualified hint request escaped");
   qualified=1;pk=0;ps=1;pt=13'h124;rows=48'hff6b646d2240;mask=255;
   sendplan();wait(done);@(negedge n);if(outs!=32||fault||hfault)$fatal(1,"actual BG after hint");cases++;
  end
  setup(1);wait(source.cache_path.cache.pending);@(negedge n);stop=1;pv=0;
  wait(drained);repeat(12)@(negedge n);
  if(active||hr||finished||tv||outs||finishes)$fatal(1,"STOP drain");
  for(integer i=0;i<7;i++)if(source.cache_path.cache.valid[i]!=0)$fatal(1,"STOP validity");
  stop=0;repeat(12)@(negedge n);if(active||hr||finished||done||tv)$fatal(1,"late DONE after STOP");cases++;
  $display("PASS HANDOFF371 cases=%0d",cases);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout handoff371");end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-source368/map01';names=['nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile205.sv','nes_native_arbiter165.sv']
 for n in names:shutil.copyfile((a.source if (a.source/n).exists() else old)/n,d/n)
 s=(a.source/'nes_plan_path267.sv').read_text();(d/'hint371.sv').write_text(s[s.index('module nes_hint361'):],newline='\n');names+=['hint371.sv']
 (d/'handoff371_tb.sv').write_text(TB,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'handoff371_tb.sv'],d,'vlog')
 raw=run(q/'vsim.exe',['-c','work.handoff371_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120);assert 'PASS HANDOFF371 cases=6' in raw
 result=dict(passed=True,cases=6,pins={str(d/n):sha(d/n) for n in names+['handoff371_tb.sv']})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS HANDOFF371 cases=6')
if __name__=='__main__':main()
