# SPDX-License-Identifier: MIT
"""Prepare210 from frozen209: sorted lookup + passive ROM reuse/bus budget.
No protocol, FPGA, source qualification, SNES client or save SRAM change.
"""
from pathlib import Path
import argparse,json
from nes_board204 import ROOT,BASE,sha,replace
from nes_board181 import copy_pins

def transform(src):
 s=src['nes_plan191.c']
 old=' for(unsigned i=0;i<s->ntiles;i++)if(s->tiles[i].tag==tag&&(s->tiles[i].kind&kind))return &s->tiles[i];'
 s=replace(s,old,''' unsigned lo=0,hi=s->ntiles;
 while(lo<hi){unsigned mid=lo+(hi-lo)/2;
  if(s->tiles[mid].tag<tag)lo=mid+1;else hi=mid;
 }
 if(lo<s->ntiles&&s->tiles[lo].tag==tag&&(s->tiles[lo].kind&kind))return &s->tiles[lo];''')
 s=replace(s,' unsigned palettes=s->counts[5]/32;', ''' /*2031 receiver enumerates strictly increasing physical tags. Reject
  * malformed direct callers before emitting any plan; never binary-search
  * an unchecked legacy/unsorted list. */
 for(unsigned i=0;i<s->ntiles;i++)if(s->tiles[i].tag>=8192||
    !s->tiles[i].kind||(s->tiles[i].kind&~3)||
    (i&&s->tiles[i-1].tag>=s->tiles[i].tag))return fail(p,6);
 unsigned palettes=s->counts[5]/32;''')
 src['nes_plan191.c']=s
 s=replace(src['nes_native_runtime165.c'],'#include "nes_trace166.h"','#include "nes_trace166.h"\n#include "nes_budget210.h"')
 s=replace(s,' s->inside_transfer=true;',' s->inside_transfer=true;unsigned opcode=tx[0];')
 s=replace(s,' s->inside_transfer=false;s->transactions++;s->wire_bytes+=n;',
 ' s->inside_transfer=false;s->transactions++;s->wire_bytes+=n;\n nes_budget210_wire(opcode,n,ok);')
 s=replace(s,'bool nes_runtime165_begin(','''static bool budget_plan210(void *ctx,const struct nes_plan191 *q){
 struct nes_native_runtime165 *s=ctx;
 if(!nes_plan200_emit(&s->plan,q))return false;
 nes_budget210_plan(q);return true;
}
bool nes_runtime165_begin(''')
 s=replace(s,' memset(s,0,sizeof(*s));',' memset(s,0,sizeof(*s));nes_budget210_reset();')
 s=replace(s,' struct nes_native165 *r=s->receiver;',' struct nes_native165 *r=s->receiver;\n nes_budget210_frame(s->ticks(s->ctx)-s->started);')
 s=replace(s,'nes_plan200_emit,&s->plan)','budget_plan210,s)')
 for phase,name in [('RECEIVE','receive'),('PLAN','build'),('SEAL','seal')]:
  needle='  ' if name!='receive' else ' '
  line=needle+'nes_trace166.'+name+'_ticks+=s->ticks(s->ctx)-nes_trace166.mark_tick;'
  s=replace(s,line,line+'\n'+needle+'nes_budget210_time(B210_'+phase+',s->ticks(s->ctx)-nes_trace166.mark_tick);')
 s=replace(s,'  nes_trace166.last_display_tick=s->ticks(s->ctx)-s->started;',
 '  nes_trace166.last_display_tick=s->ticks(s->ctx)-s->started;\n  nes_budget210_display(nes_trace166.last_display_tick,s->video);')
 src['nes_native_runtime165.c']=s
 return src

def prepare(out):
 prior=BASE/'probes/nes-binding209/arm01';p=json.loads((prior/'preparation-paired209.json').read_bytes())
 pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);changed={};added={}
 for n,s in transform({n:(prior/'src'/n).read_text() for n in ['nes_plan191.c','nes_native_runtime165.c']}).items():
  (out/'src'/n).write_text(s,encoding='utf8',newline='\n');changed['src/'+n]=sha(out/'src'/n)
 for n in ['nes_budget210.c','nes_budget210.h']:
  (out/'src'/n).write_bytes((ROOT/'src/nes/firmware'/n).read_bytes());added['src/'+n]=sha(out/'src'/n)
 for n in ['src/nes_menu_diagnostic.c','src/nes_runtime_board165.inc','src/nes_checkpoint112.c','src/VERSION','src/Makefile']:
  s=(out/n).read_text()
  if n.endswith('Makefile'):s=replace(s,'nes_plan_service200.c\n','nes_plan_service200.c nes_budget210.c\n')
  else:
   for a,b in [('NES-GAME-209','NES-GAME-210'),('GAME 209','GAME 210'),('game209.nes','game210.nes'),('fpga_n209.bi3','fpga_n210.bi3'),('last-209.txt','last-210.txt'),('NES209 seq=','NES210 seq='),('nes-progress-209.txt','nes-progress-210.txt'),('NES-GAME209-DEV','NES-GAME210-DEV')]:s=s.replace(a,b)
  if n.endswith('nes_menu_diagnostic.c'):
   s=replace(s,'#include "nes_trace166.h"','#include "nes_trace166.h"\n#include "nes_budget210.h"')
   s=replace(s,' memset(&native_runtime165,0,sizeof(native_runtime165));',' memset(&native_runtime165,0,sizeof(native_runtime165));nes_budget210_reset();')
   # Reuse the SAME4096-byte stack buffer only after normal report closes.
   # Still under the established safe-base/persist guard and USB IRQ exclusion.
   s=replace(s,' if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);', ''' int budget_n=nes_budget210_format(text,sizeof text);
 if(budget_n>0){
  UINT budget_written=0;
  FRESULT bo=f_open(&log,"/sd2snes/nes-budget-210.txt",FA_CREATE_ALWAYS|FA_WRITE),bw=bo,bc=bo;
  if(bo==FR_OK){bw=f_write(&log,text,(UINT)budget_n,&budget_written);bc=f_close(&log);}
  printf("NES210 budget open=%u write=%u close=%u bytes=%u/%u\\n",bo,bw,bc,(unsigned)budget_written,(unsigned)budget_n);
 }
 if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);''')
  if n.endswith('nes_runtime_board165.inc'):
   s=replace(s,'#include "nes_trace166.h"','#include "nes_trace166.h"\n#include "nes_budget210.h"')
   s=replace(s,'struct nes_native_video165 video;} work;','struct nes_native_video165 video;struct nes_budget210_cache budget;} work;')
   s=replace(s,' while(nes_runtime165_step(&native_runtime165)){}',' nes_budget210_attach(&work.budget);\n while(nes_runtime165_step(&native_runtime165)){}\n nes_budget210_detach();')
  (out/n).write_text(s,encoding='utf8',newline='\n');changed[n]=sha(out/n)
 r=dict(copied=pins,changed=changed,added=added,hardware_package=False,new_fpga=False,
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_budget210.py','src/nes/firmware/nes_budget210.c','src/nes/firmware/nes_budget210.h']})
 (out/'preparation-budget210.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=prepare(a.out)
 print(json.dumps(dict(changed=list(r['changed']),added=list(r['added']))))
