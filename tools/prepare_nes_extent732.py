"""727: preserve complete contiguous map extents before confirmed ordinary.

Yield only at a real address gap, retain original producer queries and pair
grants inside the extent. When all maps are issued, run719 before ordinary.
Do not interpret one DMA progress event as whole-map completion.
"""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from nes_raw506 import once,sha
from prepare_nes_tail729 import run as costs

def run(a):
 costs(SimpleNamespace(base=a.base,out=a.out,owned=False,cheap_oam=True))
 p=a.out/'nes_native_sink165.c';s=p.read_text()
 s=once(s,'   if(early!=3)break;\n   early=2;', '''   /*732 Preserve the full adjacent extent, not just one192B pair.
    * The original checked producer query/grant cadence stays unchanged. */
   if(early==4){
    if(g<64 && ((mask>>g)&1))continue;
    while(g<64 && !((mask>>g)&1))g++;
    s->map_next=(uint8_t)g;return true;
   }
   if(early!=3)break;
   early=2;''')
 # A mode4 call with no changed rows must also advertise that no map remains.
 lo=s.index('bool map527(');hi=s.index('static bool __attribute__((noinline)) same635',lo)
 part=s[lo:hi];part=once(part,' return true;\n}', ' if(early==4)s->map_next=64;\n return true;\n}')
 s=s[:lo]+part+s[hi:]
 lo=s.index(' bool same=same635(s,p);');hi=s.index(' if(!span(s,5,0,p->hdma',lo)
 ordinary=s[lo:hi].replace(' bool same=same635(s,p);\n','');s=s[:lo]+s[hi:]
 begin=s.index(' if(!map527(s,p,r->map_upload,false))return false;');end=s.index('  /* Canonical raw CHR',begin)
 prior=s[begin:end];wait=prior[prior.index(' /*719'):]
 s=s[:begin]+''' bool same=same635(s,p);
 /*732 First emit a complete map extent. If another extent remains,
  * lend its address gap to immutable ordinary and normal OBJ ownership.
  * Otherwise preserve727's bounded map-DMA opportunity before ordinary.
  * A second pass issues all remaining maps and keeps their final wait. */
 for(unsigned pass=0;;pass++){
  if(!map527(s,p,r->map_upload,pass?0:4))return false;
  if(pass || s->map_next==64){
'''+wait+'''  }
  if(pass)break;
'''+ordinary+'''  if(s->map_next==64)break;
 }
'''+s[end:]
 if a.cursor:
  # One destructive local mask cursor replaces repeated variable64-bit
  # address reconstruction and the second gap scan. Persistent mask is intact.
  s=once(s,' for(unsigned g=s->map_next&127;g<64;){\n  if(!((mask>>g)&1)){g++;pair=false;continue;}\n  unsigned first=g++,count=1;while(g<64&&count<3&&((mask>>g)&1)){g++;count++;}', ''' unsigned g=s->map_next&127;
 mask=g<64?mask>>g:0;
 while(mask){
  if(!(mask&1)){g++;mask>>=1;pair=false;continue;}
  unsigned first=g++,count=1;mask>>=1;
  while(count<3 && (mask&1)){g++;count++;mask>>=1;}''')
  s=once(s,'''    if(g<64 && ((mask>>g)&1))continue;
    while(g<64 && !((mask>>g)&1))g++;
    s->map_next=(uint8_t)g;return true;''','''    if(mask&1)continue;
    s->map_next=(uint8_t)(mask?g:64);return true;''')
 if a.shared_wait:
  # The same bounded wait is needed before ordinary on a final extent and
  # after ordinary on a partial extent. Share its body, remove pass dispatch.
  start=s.index(' bool same=same635(s,p);');end=s.index('  /* Canonical raw CHR',start)
  s=s[:start]+''' bool same=same635(s,p);
 if(!map527(s,p,r->map_upload,4))return false;
 bool last=s->map_next==64;
 if(last && !mapwait732(s))return false;
'''+ordinary+''' if(!last && (!map527(s,p,r->map_upload,0) || !mapwait732(s)))return false;
'''+s[end:]
  s=once(s,'bool nes_sink212_seal(','''static bool __attribute__((noinline)) mapwait732(struct nes_native_sink165 *s){
'''+wait+''' return true;
}
bool nes_sink212_seal(''')
 if a.direct:
  assert not a.shared_wait
  start=s.index(' bool same=same635(s,p);');end=s.index('  /* Canonical raw CHR',start)
  s=s[:start]+''' bool same=same635(s,p),after=false;
 if(!map527(s,p,r->map_upload,4))return false;
 if(s->map_next==64)goto wait732;
ordinary732:
'''+ordinary+''' if(after)goto complete732;
 after=true;
 if(!map527(s,p,r->map_upload,0))return false;
wait732:
'''+wait+''' if(!after){after=true;goto ordinary732;}
complete732:
'''+s[end:]
 p.write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe732.json')).write_text(json.dumps(dict(stage=732,cursor=a.cursor,shared_wait=a.shared_wait,direct=a.direct,scope=__doc__,base=sha(a.base/'obj-nes-100/firmware.stm'),sources={p.name:sha(p)},new_static_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--cursor',action='store_true')
 p.add_argument('--shared-wait',action='store_true')
 p.add_argument('--direct',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
