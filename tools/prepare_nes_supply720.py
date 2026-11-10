"""720: preserve719 deadlines; query real tile ownership and fence BG supply.

Replace receipt-only map priority, cap row-offer SPI to one warm offer, flush
remaining BG at the actual complete boundary before OBJ preparation when
a prior row offer occurred; no-offer frames keep the original fallback.
No generation/start-phase constants, extra storage, new wire/RTL/SNES ABI.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import sha,once

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
 '642df993cfb2bc6aa70f23a2f8a8d3172e7f2e9cfc9f2ef5b114138f6910f3a6',
 '675f54170dbe5dd3f1c2002979f88939b3c3577f9095570ba775277c503fb033')
 names=('nes_plan_service200.c','nes_planner211.c','nes_native_sink165.c');f={n:(a.base/n).read_text() for n in names}
 n=names[0];s=f[n];lo=s.index(' /* Finish the already owned bulk before continuing a warm map run.');hi=s.index(' uint8_t flags;',lo)
 f[n]=s[:lo]+''' /*720 Query the producer even after a map head. The checked receipt
  * alone cannot tell whether another capture-backed OBJ bank is ready.
  * poll retains descriptor identity, prior bulk completion and STOP. */
'''+s[hi:]
 n=names[1];s=f[n]
 s=once(s,'next_offer=g+3;if(!resident->offer_map(resident->ctx,false))',
  'next_offer=(resident->resident[resident->target][0]&1)?32:g+3;if(!resident->offer_map(resident->ctx,false))')
 s=once(s,'/* At most three rows per packet. The next trigger must be beyond\n    * every row this offer could enqueue, including with sparse masks. */',
  '/*720 One warm row offer leaves the remaining BG scan free of SPI.\n    * Cold keeps its existing row supply; final completion owns all rows. */')
 f[n]=s
 n=names[2];s=f[n]
 s=once(s,' if(s->map_next>=64)return true;',''' /*720 The final callback is after every BG group, before any OBJ lookup.
  * Flush the remaining immutable BG records through normal E8/E9 guards. */
 if(final && s->plan->bank_history==2 && !nes_plan549_first(s->plan))return false;
 if(s->map_next>=64)return true;''')
 f[n]=s
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in f.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=720,scope=__doc__,base_firmware=sha(a.base/'obj-nes-100/firmware.stm'),changed={n:sha(a.out/n) for n in names},new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
