# SPDX-License-Identifier: MIT
"""Bounded joint delta C candidate; NOT firmware or a production wire decoder."""
from pathlib import Path
import argparse,hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
PRODUCTION=BASE/'probes/nes-repeat227/arm01/src'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def once(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a));return s.replace(a,b)


def planner(s):
    s=s.replace('#include "nes_resident211.h"','#include "nes_delta231.h"')
    s=once(s,'static void map_word185(struct nes_native_video165 *p,unsigned at,unsigned word){',
        'static void map_word185(struct nes_native_video165 *p,unsigned at,unsigned word,struct nes_dirty231 *d){')
    s=once(s,'p->map_dirty|=UINT64_C(1)<<(at/64);','{p->map_dirty|=UINT64_C(1)<<(at/64);nes_dirty231_map(d,at);}')
    s=once(s,'map_word185(p,at,slot|((bank[g]*4+(cell>>13))<<10)|0x2000);','map_word185(p,at,slot|((bank[g]*4+(cell>>13))<<10)|0x2000,d);')
    s=once(s,'bool inherit,struct nes_resident211 *resident){','bool inherit,struct nes_resident211 *resident,struct nes_dirty231 *d){')
    a=s.index(' /* Keep only the old map;');b=s.index(' if(s->state!=',a);init=s[a:b];s=s[:a]+s[b:]
    marker=' /* Regroup compact rows'
    at=s.index(marker)
    s=s[:at]+''' /* Validate captured material first, then compare old output before its
  * union becomes BG/OBJ scratch. Final material is regenerated normally. */
 if(!nes_dirty231_material(d,s,lut,p))return fail(p,18);
'''+init+''' p->patch_count=s->patch_count;p->display_mask=(uint8_t)(s->raster[first_normal]>>36);
'''+s[at:]
    s=once(s,'bool nes_native_video211_plan(', 'bool nes_native_video231_plan(')
    s=once(s,'struct nes_native_video165 *p,struct nes_resident211 *resident){','struct nes_native_video165 *p,struct nes_resident211 *resident,struct nes_dirty231 *d){')
    s=once(s,'if(!resident||!p||!s)return false;', 'if(!resident||!p||!s||!d)return false;')
    s=once(s,'if(resident->fault||!resident->open', 'if(!nes_dirty231_begin(d,resident)||resident->fault||!resident->open')
    s=once(s,'!build211(s,lut,p,resident->displayed,resident)', '!build211(s,lut,p,resident->displayed,resident,d)')
    s=once(s,'p->valid=false;nes_resident211_abort(resident);return false;', 'p->valid=false;nes_resident211_abort(resident);nes_dirty231_abort(d);return false;')
    pos=s.rindex(' return true;');s=s[:pos]+' d->prepared=true;d->raw=p->patch_count!=0;\n'+s[pos:]
    return s


DIRTY_SEND=r'''
static bool dirty_span231(struct nes_native_sink165 *s,const struct nes_native_video165 *p,const struct nes_dirty231 *d,unsigned section,unsigned base,unsigned size,unsigned destination){
 uint8_t b[240];const uint8_t *bits=d->stale[d->target];unsigned chunks=(size+15)/16;
 for(unsigned g=0;g<chunks;){
  if(!(bits[(base+g)/8]&(1u<<((base+g)%8)))){g++;continue;}
  unsigned start=g++,n=1;
  while(g<chunks&&n<15&&(bits[(base+g)/8]&(1u<<((base+g)%8)))){g++;n++;}
  unsigned bytes=n*16;if(start*16+bytes>size)bytes=size-start*16;
  for(unsigned i=0;i<bytes;i++)b[i]=nes_dirty231_byte(p,section,start*16+i);
  if(!packet(s,2,section,destination+start*16,b,bytes))return false;
 }
 return true;
}
'''


def sink(s):
    s=s.replace('#include "nes_resident211.h"','#include "nes_delta231.h"')
    s=s.replace('0x2271','0x2311')
    pos=s.index('bool nes_sink212_seal(');s=s[:pos]+DIRTY_SEND+s[pos:]
    s=once(s,'bool nes_sink212_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,struct nes_resident211 *r){',
        'bool nes_sink231_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,struct nes_resident211 *r,struct nes_dirty231 *d){')
    s=once(s,' uint16_t budget=4192;', ''' if(!d||d->fault||!d->open||!d->prepared||!r||d->serial!=r->serial||d->generation!=r->generation||d->target!=r->target)return fail(s,5);
 uint16_t budget=4192;''')
    a=s.index(' for(unsigned g=0;g<64;){',s.index('bool nes_sink231_seal'));b=s.index(' if(p->patch_count){',a)
    s=s[:a]+''' if(!dirty_span231(s,p,d,2,0,4096,0)||!dirty_span231(s,p,d,3,256,512,0)||
    !oam227(s,data[2])||!span(s,5,0,data[3],size[5]))return false;
'''+s[b:]
    a=s.index('  const uint8_t *parts[4]');b=s.index('  size[5]=',a);end=s.index('\n',b)
    s=s[:a]+'''  if(!dirty_span231(s,p,d,5,288,2297,1121))return false;
  size[5]=3418;'''+s[end:]
    s=once(s,'uint8_t descriptor[168];','uint8_t descriptor[222];')
    s=once(s,'memcpy(descriptor+24,r->used,144);', 'memcpy(descriptor+24,r->used,144);memcpy(descriptor+168,d->stale[d->target],54);')
    s=once(s,'if(!nes_resident211_commit(r,s->serial,s->generation,r->target,true))return fail(s,5);',
        'if(!nes_resident211_commit(r,s->serial,s->generation,r->target,true)||!nes_dirty231_commit(d,s->serial,s->generation,r->target,true))return fail(s,5);')
    return s


def materialize(out):
    out.mkdir(parents=True,exist_ok=False);pins={}
    fixture=BASE/'probes/nes-scroll225/test02/candidate'
    for f in fixture.iterdir():
        if f.suffix not in ('.c','.h','.inc') or f.name=='host.c':continue
        src=PRODUCTION/f.name if (PRODUCTION/f.name).exists() else f
        pins[str(src.relative_to(BASE))]=sha(src);shutil.copyfile(src,out/src.name)
    for f in (ROOT/'cores/nes/candidate').glob('nes_delta231*'):
        pins[str(f.relative_to(BASE))]=sha(f);shutil.copyfile(f,out/f.name)
    for name,fn in [('nes_planner211.c',planner),('nes_native_sink165.c',sink)]:
        p=out/name;p.write_text(fn(p.read_text()),encoding='utf-8',newline='\n')
    p=out/'nes_native165.c';p.write_text(p.read_text()+'\n#include "nes_delta231_receiver.inc"\n',encoding='utf-8',newline='\n')
    p=out/'nes_native_sink165.h';s=p.read_text();s+='\nstruct nes_dirty231;\nbool nes_sink231_seal(struct nes_native_sink165 *,const struct nes_native_video165 *,struct nes_resident211 *,struct nes_dirty231 *);\n';p.write_text(s,encoding='utf-8',newline='\n')
    (out/'candidate.json').write_text(json.dumps(dict(scope=__doc__,pins=pins,generator_sha256=sha(Path(__file__)),production_bound=False),indent=2)+'\n')
    return pins


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();materialize(a.out)
