"""Resolve BG slots/plans before materializing map; reuse pre-OAM workspace."""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in ('b5c42303c6831190f77c95367bd1640e3e575caea8e3909af27e2587ad5eb600','a1408f18a82602aa54fb67607c933c7dd5de79213e43adc1d2ee185ca3ae712a')
 names=('nes_planner211.c','nes_native_runtime165.c','nes_resident211.h');f={n:(a.base/n).read_text() for n in names}
 n='nes_planner211.c';s=f[n]
 s=once(s,' unsigned next_offer=3;', ''' /* OAM/CGRAM/HDMA are not produced or published until after BG/map.
  * Use character access to the whole object representation, not a typed
  * alias crossing array bounds. 2112 slot bytes plus32 canonical row refs. */
 _Static_assert(offsetof(struct nes_native_video165,hdma)+1121-
                offsetof(struct nes_native_video165,oam)>=2144,"BG scratch");
 uint8_t *slots715=(uint8_t *)p+offsetof(struct nes_native_video165,oam);
 uint8_t *refs715=slots715+2112;''')
 lo=s.index('  /* Physical rows g and g+32');hi=s.index('  nes_cost474_groups++;',lo);s=s[:lo]+s[hi:]
 lo=s.index('   unsigned old_column=');hi=s.index('   reusable474|=',lo)
 s=s[:lo]+'   refs715[g]=refs715[reuse];\n'+s[hi:]
 s=once(s,'  if(!exceptional)reusable474|=UINT32_C(1)<<g;','  refs715[g]=(uint8_t)g;\n  if(!exceptional)reusable474|=UINT32_C(1)<<g;')
 lo=s.index('  unsigned column=(column225');hi=s.index('\n }\n\nrow549_done:',lo)
 s=s[:lo]+'  put16(slots715+(g*33+x)*2,slot);'+s[hi:]
 lo=s.index(' /* No OBJ/raw operation below writes map.');hi=s.index(' /* No callback retains scratch pointers;',lo)
 s=s[:lo]+''' /* All unique slots are now reserved for this frame. Flush pending BG
  * before spending the remaining row materialization time; no map is ready
  * merely because a plan was accepted. The original consumer checks remain. */
 if(resident->offer_map && !resident->offer_map(resident->ctx,0))return fail(p,7);
 unsigned next_offer=3;
 for(unsigned g=0;g<groups;g++){
  if(resident->offer_map && g>=next_offer &&
     ((resident->map_stale[resident->target]|p->map_dirty)&(UINT64_C(1)<<(g-3)))){
   next_offer=g+3;if(!resident->offer_map(resident->ctx,1))return fail(p,7);
  }
  for(unsigned x=0;x<33;x++){
   unsigned at=(refs715[g]*33+x)*2;
   unsigned slot=(unsigned)slots715[at]|((unsigned)slots715[at+1]<<8);
   unsigned cell=s->maps[(s->rows[first[g]]>>3)*33+x];
   unsigned column=(column225(s->raster[first[g]])+x)&63u;
   map_word185(p,((column/32)*1024+g*32+column%32)*2,
               slot|((bank[g]*4+(cell>>13))<<10)|0x2000);
  }
 }
 if(resident->offer_map && !resident->offer_map(resident->ctx,next_offer!=3?2:1))return fail(p,7);

'''+s[hi:];f[n]=s
 n='nes_resident211.h';f[n]=once(f[n],'bool (*offer_map)(void *,bool); /* true: all BG rows are final */','bool (*offer_map)(void *,unsigned); /* 0: BG plan flush;1: rows;2: map final */')
 n='nes_native_runtime165.c';s=once(f[n],'static bool offer527(void *ctx,bool final){','static bool offer527(void *ctx,unsigned phase){')
 s=once(s,' return nes_sink527_early(&s->sink,s->video,s->resident,final);',' if(!phase)return nes_plan549_first(&s->plan);\n return nes_sink527_early(&s->sink,s->video,s->resident,phase==2);');f[n]=s
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in f.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=715,base={n:sha(a.base/n) for n in names},patch={n:sha(a.out/n) for n in names},scratch_B=2144,new_static_RAM_B=0),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
