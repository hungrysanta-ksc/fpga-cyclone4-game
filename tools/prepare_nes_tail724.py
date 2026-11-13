"""724: checked ready-bulk handoff before map idle; prepare immutable tail early.

No generation/phase exception, new wait constant, state, wire, RTL or SNES ABI.
The prior map queue must still retire inside poll before a new bulk submits.
If no bulk is ready, last section remains map and719 admission is unchanged.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
 'fce656f0769de3ce15de167bfb5a54e5d7ef5f23d372e30c7118c9fd94fc8ca9',
 '5c6a2471eecadd72f5747b78105507f1bf2d78dbf407a14c7511541174167f88')
 n='nes_native_sink165.c';s=(a.base/n).read_text()
 lo=s.index('  /* Canonical raw CHR');hi=s.index(' if(same&&',lo)
 prepare=s[lo:hi];s=s[:lo]+s[hi:]
 s=once(s,' if(!map527(s,p,r->map_upload,false))return false;',prepare+''' if(!map527(s,p,r->map_upload,false))return false;
 /*724 A checked available producer may own the next queue position.
  * poll still checks STOP/CRC/identity, drains the map head and services
  * bounded input before bulk submission. No display/VRAM ownership grant. */
 if(s->plan && s->plan->bank_history==2 &&
    !nes_plan200_progress(s->plan,NES_ORDINARY553))return fail(s,5);''')
 if a.replace_palette_wait:
  lo=s.index(' /* The original span still owns packet boundaries')
  hi=s.index(' if(op==24)',lo)
  s=s[:lo]+''' /*724 Queue send/through still enforce real credit and full identity.
  * Ready-bulk handoff replaces four unconditional palette-tail drains. */
'''+s[hi:]
 a.out.mkdir(parents=True,exist_ok=False);(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=724,replace_palette_wait=a.replace_palette_wait,base=sha(a.base/'obj-nes-100/firmware.stm'),source=sha(a.out/n),scope=__doc__,new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--replace-palette-wait',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
