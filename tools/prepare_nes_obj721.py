"""721 isolated query A; DMA-notice ownership B and resource-only C/D/E.

A removes receipt-only return. B retains719 map priority until a current
checked DMA notice. C moves notice invalidation to E1. D merges token
comparisons, E additionally merges repeat-completion return. No variant is
selected; full two-phase replay is A only. No new state or wire/RTL/SNES ABI.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import sha,once

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
 '642df993cfb2bc6aa70f23a2f8a8d3172e7f2e9cfc9f2ef5b114138f6910f3a6',
 '675f54170dbe5dd3f1c2002979f88939b3c3577f9095570ba775277c503fb033')
 n='nes_plan_service200.c';s=(a.base/n).read_text();original=s
 lo=s.index(' /* Finish the already owned bulk before continuing a warm map run.');hi=s.index(' uint8_t flags;',lo)
 s=s[:lo]+''' /*721 Query actual tile ownership; keep719 row/map callbacks unchanged.
  * The original poll validates CRC/identity, completes the prior bulk and
  * observes STOP before submitting. It cannot grant a display ACK. */
'''+s[hi:]
 if a.variant in ('B','C','D','E'):
  s=once(original,'p->bulk_valid && (p->bulk[1] || p->bulk[4] || p->bulk[5])){',
   'p->bulk_valid && (p->bulk[1] | p->bulk[4] | p->bulk[5]) &&\n    (!(p->window->status_flags&8) || p->window->sent!=p->window->retired)){')
  s=once(s,' /* Finish the already owned bulk before continuing a warm map run.',
   ' /*721B A checked empty-queue DMA notice permits a producer query.\n  * A stale notice after E1 cannot pass sent==retired. No new wait/poll.\n  * Finish the already owned bulk before continuing a warm map run.')
 if a.variant in ('D','E'):
  s=once(s,'if(p->bulk_valid&&token485(d)==token485(p->bulk)){',
   'if(p->bulk_valid&&token485(d)<=token485(p->bulk)){')
  s=once(s,'   if(p->bulk_valid&&token485(d)<token485(p->bulk))return status215(p,phase,NES_PLAN215_DESCRIPTOR,rx);\n','')
 if a.variant=='E':
  s=once(s,'    if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;\n    *flags=result;return true;',
   '    *flags=result;return phase!=NES_PLAN215_FINISH || complete485(p);')
 extra={}
 if a.variant=='C':
  s=once(s,'(!(p->window->status_flags&8) || p->window->sent!=p->window->retired)',
   '!(p->window->status_flags&8)')
  s=s.replace('A stale notice after E1 cannot pass sent==retired.', 'The window clears the advisory notice at every successful E1.')
  name='nes_sink_window184.c';w=(a.base/name).read_text()
  w=once(w,' s->sent++;s->ever_sent=true;memcpy(s->last,p,10);return true;',
   ' s->sent++;s->ever_sent=true;s->status_flags&=(uint8_t)~8;memcpy(s->last,p,10);return true;')
  extra[name]=w
 a.out.mkdir(parents=True,exist_ok=False);(a.out/n).write_text(s,encoding='utf8',newline='\n')
 for name,w in extra.items():(a.out/name).write_text(w,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=721,variant=a.variant,scope=__doc__,base_firmware=sha(a.base/'obj-nes-100/firmware.stm'),changed={p.name:sha(p) for p in a.out.iterdir()},new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--variant',choices=('A','B','C','D','E'),default='A')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
