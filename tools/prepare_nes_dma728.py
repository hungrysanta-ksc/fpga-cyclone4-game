"""Share719 bounded map-DMA admission between SEAL and new OBJ ownership.

Keep727 adjacent map pair and BG supply. Existing checked E0 progress, credit,
STOP and the existing ACK-relative expiry bound own the opportunity. No new
delay constant, generation exception, persistent state or consumer priority.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in ('3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386','523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655')
 n='nes_native_sink165.c';s=(a.base/n).read_text()
 begin=s.index(' /*719 The ACK timestamp');end=s.index('  /* Canonical raw CHR',begin)
 s=s[:begin]+' if(!nes_sink728_map_wait(s,false))return false;\n'+s[end:]
 helper='''/*728 Share actual map credit/progress and719 expiry with OBJ handoff.
 * single is the existing BG one-input opportunity; it must not delay ROM.
 * A missing event or expired clock is not a display failure. */
bool nes_sink728_map_wait(struct nes_native_sink165 *s,bool single){
 struct nes_plan200 *p=s->plan;
 if(!p || p->bank_history!=2 || !p->window || p->window->last[1]!=2)return true;
 struct nes_sink_window184 *w=p->window;
 uint32_t now=0,until=0;
 if(!single){
  if(!nes_cost471_available)return true;
  now=nes_cost471_now();uint32_t age=now-s->ack_clock719;
  until=1397700u-age%1397700u;
  if(age>=(1u<<26) || until>=672000u)return true;
 }
 uint8_t ack[12];unsigned left=single?1:w->poll_limit;
 while(left--){
  if(!single && nes_cost471_now()-now>=until)break;
  if(!nes_window184_drain(w,ack))return fail(s,5);
  if((w->status_flags&8) || !w->wait)break;
  if(!w->wait(w->ctx,w->guard,4,false))return fail(s,5);
 }
 return true;
}
'''
 s=once(s,'bool nes_sink212_seal(',helper+'bool nes_sink212_seal(')
 if a.unified_clock:
  s=once(s,' if(!nes_sink728_map_wait(s,false))return false;',' if(!nes_sink728_map_wait(s,false))return fail(s,5);')
  s=once(s,' uint32_t now=0,until=0;',' uint32_t now=nes_cost471_now(),until=UINT32_MAX;')
  s=once(s,'  now=nes_cost471_now();uint32_t age=now-s->ack_clock719;','  uint32_t age=now-s->ack_clock719;')
  s=once(s,''' while(left--){
  if(!single && nes_cost471_now()-now>=until)break;
  if(!nes_window184_drain(w,ack))return fail(s,5);''',''' while(left-- && nes_cost471_now()-now<until){
  if(!nes_window184_drain(w,ack))return false;''')
  s=once(s,'  if(!w->wait(w->ctx,w->guard,4,false))return fail(s,5);','  if(!w->wait(w->ctx,w->guard,4,false))return false;')
 files={n:s}
 n='nes_plan_service200.c';s=(a.base/n).read_text()
 start=s.index('   /* A new ready tile follows');end=s.index('   if(!nes_sink195_submit',start)
 s=s[:start]+'''   /*728 BG retains its single checked opportunity. OBJ can lend the
    * accepted map the existing bounded DMA window; descriptor stays local
    * until submit succeeds, then owns its separate actual receipt. */
   if(p->ending && !nes_sink728_map_wait(p->sink,d[1]==0))return fail(p,5);
'''+s[end:]
 files[n]=s
 n='nes_native_sink165.h';files[n]=once((a.base/n).read_text(),'bool nes_sink212_seal(', 'bool nes_sink728_map_wait(struct nes_native_sink165 *,bool);\nbool nes_sink212_seal(')
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in files.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=728,unified_clock=a.unified_clock,base=sha(a.base/'obj-nes-100/firmware.stm'),scope=__doc__,sources={n:sha(a.out/n) for n in files},new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--unified-clock',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
