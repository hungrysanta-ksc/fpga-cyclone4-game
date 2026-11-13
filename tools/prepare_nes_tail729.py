"""727: share exact span cost calculation and lend known bulk queue credit.

Ordinary may enqueue behind an already owned descriptor, reserving one slot.
No new E8 response is assumed, no completion is published, FINAL still polls
and drains. BG/map production and719 bounded DMA policy remain unchanged.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in ('3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386','523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655')
 n='nes_native_sink165.c';s=(a.base/n).read_text()
 lo=s.index('static unsigned span_cost227(');hi=s.index('static bool oam227(',lo)
 helper=s[lo:hi]
 helper=once(helper,' return old<split?old:split;',' /*729 Low bit selects split only on strict savings; remaining bits keep\n  * the exact old cost for OAM selection. Maximum input remains4096B. */\n return ((old<split?old:split)<<1)|(split<old);')
 s=s[:lo]+s[hi:]
 lo=s.index(' unsigned oldcost=0,newcost=0;');hi=s.index(' /* Synchronous immutable source:',lo)
 s=s[:lo]+' bool split=span_cost227(b,n)&1u;\n'+s[hi:]
 s=once(s,'if(newcost<oldcost)count=span_piece','if(split)count=span_piece')
 s=once(s,'static bool span(',helper+'static bool span(')
 for arg in ('b,first','b+512,32','b,544'):
  s=once(s,'span_cost227('+arg+')','(span_cost227('+arg+')>>1)')
 if a.cheap_oam:
  s=once(s,' unsigned cost=(first?', ''' /*729 Short/uniform tails always use the original span. Avoid computing
  * a rejected4B-tail cost;32B high attributes cannot contain a64B run. */
 if(length<64||repeat_bytes(b+first,length)==length)return span(s,4,0,b,544);
 unsigned cost=(first?''')
  s=once(s,'(span_cost227(b+512,32)>>1)','data_cost(b+512,32)')
  s=once(s,'if(length<64||repeat_bytes(b+first,length)==length||cost>=','if(cost>=')
 files={n:s}
 if a.owned:
  n='nes_plan_service200.c';s=(a.base/n).read_text()
  s=once(s,' if(p->finished)return valid(p);',''' /*729 The descriptor already owns a FIFO position and receipt. Reuse
  * conservative cached credit for ordinary only; E1 still checks STOP and
  * real credit. Reserve a slot and never bypass FINAL or pending E9. */
 if(p->finished || (mode==NES_ORDINARY553 && !p->count && p->bulk_pending &&
    p->window && (uint16_t)(p->window->sent-p->window->retired)<=2))return valid(p);''')
  files[n]=s
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in files.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=729,owned=a.owned,cheap_oam=a.cheap_oam,base=sha(a.base/'obj-nes-100/firmware.stm'),scope=__doc__,sources={n:sha(a.out/n) for n in files},new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--owned',action='store_true');p.add_argument('--cheap-oam',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
