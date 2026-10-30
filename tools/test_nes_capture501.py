# SPDX-License-Identifier: MIT
"""501 actual PPU/raw-row recovery candidate, never a hardware/FPS claim."""
import argparse,json,shutil
from pathlib import Path
import test_nes_capture500 as base
ROOT=base.ROOT
OVERRIDES=['nes_native_planes165.sv','nes_native_frame201.sv']

def prepare(a):
 base.prepare(a.board,a.reference,a.out,a.focus,a.phase_sweep)
 m=json.loads((a.out/'inputs.json').read_text())
 for n in OVERRIDES:
  shutil.copy2(ROOT/'src/fpga/nes_capture501'/n,a.out/n);m['sources'][n]=base.sha(a.out/n)
 s=(a.out/'capture500_tb.sv').read_text()
 s=s.replace(' wire owned,geometry_valid;'," integer guard=0;initial void'($value$plusargs(\"GUARD=%d\",guard));\n wire owned,geometry_valid;")
 s=s.replace('.bg_high(bg_high),.obj_low(obj_low)', '.bg_high(bg_high && !(guard==11 && scanline==192 && cycle==16)),.obj_low(obj_low)')
 s=s.replace(".rom_fault(1'b0)",".rom_fault(guard==4 && scanline==193 && cycle==333)")
 s=s.replace(".ppu_valid(1'b1)",".ppu_valid(!(guard==2 && scanline==193 && cycle==336))")
 s=s.replace(".physical_address(22'h200000+{9'd0,vram_addr[12:0]})", """.physical_address((22'h200000+{9'd0,vram_addr[12:0]}) ^
 ((scanline==193 && cycle==336)?(guard==1?22'h020000:guard==3?22'd1:guard==12?22'd8:22'd0):22'd0))""")
 s=s.replace(".release_frame(1'b0)",".release_frame(stop_request)")
 s=s.replace(".query(1'b0),.query_kind(3'd0),.query_index(13'd0),.query_generation(16'd0)",
  ".query(query_request),.query_kind(3'd4),.query_index(13'd0),.query_generation(query_gen)")
 s=s.replace(' wire owned,geometry_valid;', ' reg stop_request=0,query_request=1;reg [15:0] query_gen=0;integer stop_count=0,dropped_high=0;\n wire owned,geometry_valid;')
 s=s.replace('while(!owned)begin','while(!owned && stop_count<64)begin')
 s=s.replace('  ce=0;write=0;',"""  ce=0;write=0;
  if(guard==11 && dropped_high!=1)$fatal(1,"missing high fault was not injected");
  query_request=1;query_gen=generation+1;
  repeat(4)begin @(negedge clk);if(capture.hit)$fatal(1,"wrong generation query");end
  query_gen=generation;
  repeat(4)@(negedge clk);
  if(capture.hit!==geometry_valid)$fatal(1,"sealed query gate");
  if(guard==10 && (owned || capture.active || capture.pixels.active || capture.compact.active || capture.raster.active))
   $fatal(1,"STOP left a member active/owned");
  query_request=0;""")
 s=s.replace(' always @(posedge clk)sampled_ce',""" always @(posedge clk)if(ce && guard==11 && scanline==192 && cycle==16 && bg_high)dropped_high++;
 always @(negedge clk)begin
  if(!owned && capture.hit)$fatal(1,"early query hit");
  if(!owned)query_gen=generation;
  if(guard==10 && ((scanline==193 && cycle==100) || stop_count!=0))begin
   stop_count++;stop_request=stop_count<4;query_request=1;query_gen=generation;
  end
  if(guard==5 && scanline==193 && cycle==100)force capture.pixels.rows.pixel_valid=0;
  else release capture.pixels.rows.pixel_valid;
  if(guard==6 && scanline==193 && cycle==258)force capture.fetch.committed_row=255;
  else release capture.fetch.committed_row;
  if(guard==7 && scanline==193 && cycle==258)force capture.fetch.row_patched=0;
  else release capture.fetch.row_patched;
  if(guard==8)force capture.patch_generation=0;
  if(guard==9)force capture.pixels.need_patch=1;
 end
 always @(posedge clk)sampled_ce""")
 s=s.replace('if(at!=events || pixel_count!=57344)', 'if(guard==0 && (at!=events || pixel_count!=57344))')
 s=s.replace('for(integer i=0;i<patches;i++)for', 'for(integer i=0;i<(guard==0?patches:0);i++)for')
 (a.out/'capture500_tb.sv').write_text(s)
 m['testbench_SHA256']=base.sha(a.out/'capture500_tb.sv')
 if a.edges:
  for name,events in [('capture-edge',[[7,256,1,0],[8,1,1,24]]),('last-row',[[231,20,1,0],[231,60,1,24]])]:
   c=dict(name=name,frame=None,delay=0,address_writes=False,events=events);m['cases'].append(c)
   (a.out/(name+'.txt')).write_text(''.join(' '.join(map(str,r))+'\n' for r in events))
 if a.guards:
  witness=next(c for c in m['cases'] if c['name']=='f699-addr1-d0')
  m['cases']=[dict(witness,name='guard'+str(i),guard=i) for i in (map(int,a.guard_list.split(',')) if a.guard_list else range(1,13))]
  for c in m['cases']:(a.out/(c['name']+'.txt')).write_text(''.join(' '.join(map(str,r))+'\n' for r in c['events']))
 if a.focus and not a.guards:
  order={n:i for i,n in enumerate(a.focus.split(','))};m['cases'].sort(key=lambda c:order.get(c['name'],len(order)))
 (a.out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

def run(a):
 # Reuse500 compiler, source pin checks and exact-pixel observer. Inject only
 # the explicit negative input selected by the case, one licensed run at a time.
 original=base.subprocess.run
 def launch(args,**kw):
  for x in args:
   if x.startswith('+STIMULUS=guard'):args=[*args,'+GUARD='+x.split('guard')[1].split('.')[0]];break
  return original(args,**kw)
 base.subprocess.run=launch
 base.run(a.out,a.questa_bin)
 r=json.loads((a.out/'result.json').read_text())
 for x in r['results']:
  expected=0 if 'guard' in x['case'] else 1
  assert x['summary'].startswith('valid='+str(expected)+' '),x
 print('PASS501',len(r['results']),'expected verdicts')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
 for n in ['board','reference','out','questa-bin']:p.add_argument('--'+n,type=Path)
 p.add_argument('--focus');p.add_argument('--phase-sweep',action='store_true');p.add_argument('--guards',action='store_true');p.add_argument('--edges',action='store_true');p.add_argument('--guard-list')
 a=p.parse_args()
 if a.mode=='prepare':prepare(a)
 else:run(a)
