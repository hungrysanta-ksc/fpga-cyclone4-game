"""Yield only at a completed727 map pair, then send immutable palette/OAM.

The final prepared resident owns these bytes. Ordinary uses the existing
checked producer/credit path, so its consumption overlaps subsequent OBJ
production without granting a receipt or display ACK early.
"""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from nes_raw506 import once,sha
from prepare_nes_tail729 import run as costs

def run(a):
 costs(SimpleNamespace(base=a.base,out=a.out,owned=False,cheap_oam=True))
 p=a.out/'nes_native_sink165.c';s=p.read_text()
 s=once(s,'   if(early!=3)break;\n   early=2;', '''   /*731 Final prepared output yields only after the producer-granted
    * adjacent192B packet, never between its384B pair. A gap or short
    * extent already ends the original grant. No new persistent cursor. */
   if(early==4){if(!pair)break;}
   else {if(early!=3)break;early=2;}''')
 lo=s.index(' bool same=same635(s,p);');hi=s.index(' if(!span(s,5,0,p->hdma',lo)
 ordinary=s[lo:hi];s=s[:lo]+s[hi:]
 s=once(s,' if(!map527(s,p,r->map_upload,false))return false;', ''' /*731 Resident/geometry validation above is complete. Keep the first
  * accepted map pair contiguous, then run ordinary's real bulk service.
  * Subsequent map starts query again because ordinary changed last head. */
 if(!map527(s,p,r->map_upload,4))return false;
'''+ordinary+''' if(!map527(s,p,r->map_upload,false))return false;''')
 p.write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe731.json')).write_text(json.dumps(dict(stage=731,scope=__doc__,base=sha(a.base/'obj-nes-100/firmware.stm'),sources={p.name:sha(p)},new_static_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
