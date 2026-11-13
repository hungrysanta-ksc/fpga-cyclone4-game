"""719 candidate: bounded DMA opportunity, relative to the last checked ACK.

This is an admission estimate, NOT beam ownership or a display permission.
NTSC/84MHz replay contract; 8ms includes the observed reuse-tail cost plus
phase/driver allowance. Full schedule gates must validate it before selection.
No generation, fixture index, boot condition or replay start is consulted.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
  'ed03f17450b41b1617e9306c43100d0c9e9a1ea6256d815c24bf2547ab8381c8',
  'a08cbf4585e14aedea2570e979de3b3468ceec08e186cb317b9ba1a8c76a190f')
 n='nes_native_sink165.c';s=(a.base/n).read_text()
 begin=s.index(' /* Allow a long accepted map tail');end=s.index('  /* Canonical raw CHR',begin)
 s=s[:begin]+''' /*719 The ACK timestamp is an estimate of periodic opportunity only.
  * Never wait while the current period still has the reuse-tail budget.
  * A missed opportunity expires; lack of DMA is not a display fault.
  * STOP and the checked E0/credit path still precede every next iteration. */
 if(s->plan && s->plan->bank_history==2 && s->plan->window &&
    s->plan->window->last[1]==2 && nes_cost471_available){
  uint32_t now=nes_cost471_now(),age=now-s->ack_clock719;
  enum {period719=1397700u,tail719=672000u};
  uint32_t phase=age%period719,until=period719-phase;
  if(age<(1u<<26) && until<tail719){
   struct nes_sink_window184 *w=s->plan->window;uint8_t ack[12];
   unsigned left=w->poll_limit;
   while(left-- && nes_cost471_now()-now<until){
    if(!nes_window184_drain(w,ack))return fail(s,5);
    if((w->status_flags&8) || !w->wait)break;
    if(!w->wait(w->ctx,w->guard,4,false))return fail(s,5);
   }
  }
 }
'''+s[end:]
 s=once(s,''' if((((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu && s->plan){
  for(unsigned i=0;i<2;i++)
   if(!nes_cost474_pause(s->plan->ctx,s->plan->guard,0,false))return fail(s,5);
 }
''','')
 s=once(s,' unsigned bank=r->target;',' s->ack_clock719=nes_cost471_now();\n unsigned bank=r->target;')
 h='nes_native_sink165.h';header=(a.base/h).read_text()
 header=once(header,' uint32_t ack635[2];',' uint32_t ack_clock719; /* Set only after checked final display ACK. */\n uint32_t ack635[2];')
 a.out.mkdir(parents=True,exist_ok=False)
 for name,body in ((n,s),(h,header)):(a.out/name).write_text(body,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=719,
  base_firmware=sha(a.base/'obj-nes-100/firmware.stm'),changed={x:sha(a.out/x) for x in (n,h)},
  new_static_RAM_B=4,new_RTL=False,new_65816=False,deadline_estimate_not_beam_permission=True),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
