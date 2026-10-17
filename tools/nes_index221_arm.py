# SPDX-License-Identifier: MIT
"""221 exact-slot indexing plus bounded phase/ingress decomposition; FPGA220 reused."""
from pathlib import Path
import argparse,json,shutil
from nes_runtime213 import ROOT,BASE,sha,once
from nes_board181 import copy_pins

def instrumentation(s):
 s=once(s,' if(!nes_plan200_emit(&s->plan,q))return false;', ''' uint32_t mark=s->ticks(s->ctx);
 bool ok=nes_plan200_emit(&s->plan,q);
 nes_budget210.bins[nes_budget210.bin][B210_COMPLEX]+=s->ticks(s->ctx)-mark;
 if(!ok)return false;''')
 needle='bool nes_runtime165_begin('
 helper='''/* Includes synchronous emit callbacks. Subtract callback ticks only for
 * completed frames, allowing10ms quantization; not a cycle-accurateCPU meter. */
static bool planner221(struct nes_native_runtime165 *s){
 uint32_t mark=s->ticks(s->ctx);
 bool ok=nes_native_video211_plan(s->receiver,s->palette,s->video,s->resident);
 nes_budget210.bins[nes_budget210.bin][B210_REUSE_PLAN]+=s->ticks(s->ctx)-mark;
 return ok;
}
'''
 s=once(s,needle,helper+needle)
 return once(s,'!nes_native_video211_plan(r,s->palette,s->video,s->resident)','!planner221(s)')

def prepare(out):
 prior=BASE/'probes/nes-status220/arm01';p=json.loads((prior/'preparation-status220.json').read_bytes())
 pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);src=out/'src'
 for ext in ['c','h']:shutil.copyfile(ROOT/f'src/nes/firmware/nes_resident221.{ext}',src/f'nes_resident211.{ext}')
 f=src/'nes_native_runtime165.c';f.write_text(instrumentation(f.read_text()),encoding='utf8',newline='\n')
 f=src/'nes_budget210.h';s=f.read_text();a=s.index('/* Passive,');b=s.index('enum {',a)
 s=s[:a]+'''/*221 actual-slot counters.5s frame-start bins,10ms ticks.
 * REUSE_PLAN=planner inclusive ticks, COMPLEX=its emit callback ticks.
 * D1_PAYLOAD=attempted encoded record bytes (not decoded useful geometry);
 * D0_CLOCK=attempted status clock bytes. No PSRAM/VBlank inference. */
'''+s[b:]
 s=once(s,'B210_BG,B210_OBJ,B210_MAP_DIRTY,B210_FIELDS','B210_BG,B210_OBJ,B210_MAP_DIRTY,B221_D1_PAYLOAD,B221_D0_CLOCK,B210_FIELDS')
 f.write_text(s,encoding='utf8',newline='\n')
 f=src/'nes_budget210.c';s=f.read_text()
 s=once(s,' nes_budget210.bins[nes_budget210.bin][f]+=n;',''' nes_budget210.bins[nes_budget210.bin][f]+=n;
 if(op==0xd1&&n>=3)nes_budget210.bins[nes_budget210.bin][B221_D1_PAYLOAD]+=n-3;
 if(op==0xd0)nes_budget210.bins[nes_budget210.bin][B221_D0_CLOCK]+=n;''')
 s=s.replace('budget_schema=215','budget_schema=221').replace('slot_hits,reserved0,reserved1','slot_hits,planner_ticks,callback_ticks').replace('bg,obj,mapdirty\\n','bg,obj,mapdirty,d1_payload,d0_clock\\n')
 f.write_text(s,encoding='utf8',newline='\n')
 for name in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
  f=src/name;s=f.read_text()
  for x,y in [('NES-GAME-220','NES-GAME-221'),('GAME 220','GAME 221'),('game220.nes','game221.nes'),('fpga_n220.bi3','fpga_n221.bi3'),('last-220.txt','last-221.txt'),('NES220','NES221'),('nes-progress-220.txt','nes-progress-221.txt'),('nes-budget-220.txt','nes-budget-221.txt'),('NES-GAME220-DEV','NES-GAME221-DEV')]:s=s.replace(x,y)
  f.write_text(s,encoding='utf8',newline='\n')
 changed={n:sha(out/n) for n in pins if sha(out/n)!=pins[n]}
 assert set(changed)=={'src/'+n for n in ['nes_resident211.c','nes_resident211.h','nes_native_runtime165.c','nes_budget210.c','nes_budget210.h','nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']}
 public=['tools/nes_index221_arm.py','src/nes/firmware/nes_resident221.c','src/nes/firmware/nes_resident221.h']
 r=dict(copied=pins,changed=changed,added={},public_sources={n:sha(ROOT/n) for n in public},index_bytes=2816,extra_static_bins_bytes=96,
        schema=221,wire_protocol_unchanged=True,new_fpga=False,physical=False)
 (out/'preparation-index221.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(changed))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
