"""718B: real map DMA event before ordinary, lending bounded next-input work.

Keep717 runtime and palette policy. Replace OAM repeated drains and map-tail
mask heuristic with checked, poll-limit-bounded event ownership. No timed wait.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
  'ed03f17450b41b1617e9306c43100d0c9e9a1ea6256d815c24bf2547ab8381c8',
  'a08cbf4585e14aedea2570e979de3b3468ceec08e186cb317b9ba1a8c76a190f')
 n='nes_native_sink165.c';s=(a.base/n).read_text()
 begin=s.index(' /* The original span still owns packet boundaries')
 end=s.index(' if(op==24)',begin);s=s[:begin]+s[end:]
 begin=s.index(' /* Allow a long accepted map tail')
 end=s.index('  /* Canonical raw CHR',begin)
 s=s[:begin]+''' /*718B Retire the last warm map head, then wait for actual map DMA
  * progress before ordinary can occupy its idle opportunity. Input may lend
  * useful work but an empty D0 is not completion. Each iteration validates
  * E0 identity/CRC and STOP; the existing poll bound rejects a stuck owner. */
 if(s->plan && s->plan->bank_history==2 && s->plan->window &&
    s->plan->window->last[1]==2){
  struct nes_sink_window184 *w=s->plan->window;uint8_t ack[12];
  unsigned left=w->poll_limit;
  for(;;){
   if(!nes_window184_drain(w,ack))return fail(s,5);
   if(w->status_flags&8)break;
   if(!left-- || !w->wait || !w->wait(w->ctx,w->guard,4,false))return fail(s,5);
  }
 }
'''+s[end:]
 a.out.mkdir(parents=True,exist_ok=False);(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage='718B',base_firmware=sha(a.base/'obj-nes-100/firmware.stm'),
  changed={n:sha(a.out/n)},new_static_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
