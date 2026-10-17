# SPDX-License-Identifier: MIT
"""Prepare actual210 geometry planner with candidate stable destination slots.
Not a deployed SPI/65816 protocol, and not a new physical performance claim.
"""
from pathlib import Path
import argparse, hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,old,new):
    assert s.count(old)==1,(old[:100],s.count(old))
    return s.replace(old,new)
def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    src=BASE/'probes/nes-budget210/arm03/src'
    preparation=json.loads((src.parent/'preparation-budget210.json').read_bytes())
    pinned=preparation['copied']|preparation['changed']|preparation['added']
    names=['nes_plan191.c','nes_plan191.h','nes_native165.h','nes_native165.c','nes_native_video165.h','nes_trace166.h','nes_trace166.c']
    pins={}
    for name in names:
        f=src/name;assert sha(f)==pinned['src/'+name]
        pins[str(f.relative_to(BASE))]=sha(f);shutil.copyfile(f,out/name)
    s=(src/'nes_plan191.c').read_text()
    start=s.index('static unsigned bg_slot(');end=s.index('bool nes_native_video191_plan(',start)
    s=s[:start]+s[end:]
    s=once(s,'#include "nes_plan191.h"','#include "nes_resident211.h"')
    s=once(s,'bool nes_native_video191_plan(const struct nes_native165 *s,const uint16_t lut[64],struct nes_native_video165 *p,bool inherit,nes_plan191_fn plan,void *ctx){',
             'static bool build211(const struct nes_native165 *s,const uint16_t lut[64],struct nes_native_video165 *p,bool inherit,struct nes_resident211 *resident){')
    s=once(s,'if(!s||!lut||!p||!plan)return false;','if(!s||!lut||!p||!resident)return false;')
    s=once(s,'if(!plan(ctx,&q))return fail(p,14);}',
             'if(nes_resident211_slot(resident,p,0,&q)!=0)return fail(p,14);}')
    s=once(s,'''  unsigned previous=p->bg_count,slot=bg_slot(p,key);if(slot==1024)return fail(p,7);
  if(slot==previous){
   q.slot=(uint16_t)slot;if(!plan(ctx,&q))return fail(p,14);
  }''','''  unsigned slot=nes_resident211_slot(resident,p,key,&q);
  if(slot>=1024)return fail(p,7);''')
    s=once(s,'''   unsigned previous=p->obj_count,slot=obj_slot(p,tag|((unsigned)masks[e]<<13));if(slot==128)return fail(p,13);
   if(slot==previous){
    q.slot=(uint16_t)slot;if(!plan(ctx,&q))return fail(p,14);
   }''','''   unsigned slot=nes_resident211_slot(resident,p,tag|((unsigned)masks[e]<<13),&q);
   if(slot>=128)return fail(p,13);''')
    s+='''
bool nes_native_video211_plan(const struct nes_native165 *s,const uint16_t lut[64],
                             struct nes_native_video165 *p,struct nes_resident211 *resident){
 if(!resident||!p||!s)return false;
 if(resident->fault||!resident->open||resident->prepared||resident->generation!=s->generation||
    !build211(s,lut,p,resident->displayed,resident)||
    !nes_resident211_prepare(resident,p->map_dirty)){
  p->valid=false;nes_resident211_abort(resident);return false;
 }
 return true;
}
'''
    (out/'nes_planner211.c').write_text(s,encoding='utf8',newline='\n')
    for name in ['nes_resident211.c','nes_resident211.h']:
        f=ROOT/'src/nes/firmware'/name;shutil.copyfile(f,out/name);pins[str(f.relative_to(BASE))]=sha(f)
    ref=BASE/'probes/nes-metadata203/test04'
    for name in ['reference203.c','reference203.h']:
        f=ref/name;shutil.copyfile(f,out/name);pins[str(f.relative_to(BASE))]=sha(f)
    # Reuse the actual reference scene builder; no duplicated compatibility parser.
    original=(ref/'host203.c').read_text();start=original.index('static void scene(');end=original.index('#include "nes_native_runtime165.h"',start)
    (out/'scene203.inc').write_text(original[start:end],encoding='utf8',newline='\n')
    pins[str((ref/'host203.c').relative_to(BASE))]=sha(ref/'host203.c')
    host=ROOT/'tests/nes-functional/resident211_host.c';shutil.copyfile(host,out/host.name)
    pins[str(host.relative_to(BASE))]=sha(host)
    result=dict(candidate=211,inputs=pins,generated={n:sha(out/n) for n in ['nes_planner211.c','scene203.inc']},
                deployed=False,spi_snes_consumer='future protocol; host consumer model only')
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.out)))
