# SPDX-License-Identifier: MIT
"""Generate sparse212 transport from pinned210 production sink. No release."""
from pathlib import Path
import json,shutil
from nes_resident211 import ROOT,BASE,sha,once

def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 src=BASE/'probes/nes-budget210/arm03/src';pins={}
 for name in ['nes_native_sink165.c','nes_native_sink165.h','nes_sink_trace168.c','nes_sink_trace168.h','nes_sink_bulk195.h','nes_sink_bulk195.inc','nes_sink_window184.c','nes_sink_window184.h']:
  f=src/name;shutil.copyfile(f,out/name);pins[name]=sha(f)
 h=out/'nes_native_sink165.h';s=h.read_text();s=once(s,'#endif','''struct nes_resident211;
bool nes_sink212_begin(struct nes_native_sink165 *,struct nes_resident211 *);
bool nes_sink212_seal(struct nes_native_sink165 *,const struct nes_native_video165 *,struct nes_resident211 *);
#endif''');h.write_text(s,encoding='utf8')
 f=out/'nes_native_sink165.c';s=f.read_text();s=once(s,'#include <string.h>','#include <string.h>\n#include "nes_resident211.h"')
 a=s.index('bool nes_sink165_begin(');b=s.index('bool nes_sink165_seal(',a)
 s=s[:a]+'''bool nes_sink165_begin(struct nes_native_sink165 *s,uint16_t gen){(void)gen;return fail(s,5);}
bool nes_sink165_pattern(void *ctx,unsigned kind,unsigned slot,const uint8_t *b,unsigned n){
 (void)kind;(void)slot;(void)b;(void)n;return fail(ctx,5);
}
bool nes_sink212_begin(struct nes_native_sink165 *s,struct nes_resident211 *r){
 if(!r||r->fault||!r->open||r->prepared||s->state!=NES_SINK165_IDLE||
    s->serial==UINT32_MAX||r->serial!=s->serial+1||r->displayed!=s->displayed||
    r->target!=(s->displayed?(s->serial&1u):0))return fail(s,5);
 uint8_t b[12];put16(b,0x2121);put16(b+2,r->target);
 for(unsigned i=0;i<4;i++){b[4+i]=(uint8_t)(s->serial>>(8*i));b[8+i]=(uint8_t)(r->epoch>>(8*i));}
 s->serial=r->serial;s->generation=r->generation;s->sequence=0;s->bg_next=s->obj_next=0;
 if(!packet(s,1,0,0,b,sizeof b))return false;
 s->state=NES_SINK165_BUILD;return true;
}
bool nes_sink165_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,uint16_t budget){
 (void)p;(void)budget;return fail(s,5);
}
''' +s[b:]
 s=once(s,'bool nes_sink165_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,uint16_t budget){\n if(s->state', 'bool nes_sink212_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,struct nes_resident211 *r){\n uint16_t budget=4192;\n if(!r||r->fault||!r->prepared||!r->open||!s->serial||r->serial!=s->serial||r->generation!=s->generation||r->target!=((s->serial-1)&1u)||r->displayed!=s->displayed)return fail(s,5);\n for(unsigned i=0;i<144;i++)if(r->used[i]&~(r->resident[r->target][i]|r->dirty[i]))return fail(s,5);\n if(s->state')
 s=once(s,'p->bg_count!=s->bg_next||!s->bg_next||p->obj_count!=s->obj_next||','!p->bg_count||p->bg_count>1024||p->obj_count>128||')
 s=once(s,' if(!map185(s,p))return false;', ''' for(unsigned g=0;g<64;){
  if(!((r->map_upload>>g)&1)){g++;continue;}
  unsigned first=g++,count=1;while(g<64&&count<3&&((r->map_upload>>g)&1)){g++;count++;}
  if(!packet(s,2,2,first*64,p->map+first*64,count*64))return false;
 }''')
 s=once(s,'uint8_t descriptor[24];','uint8_t descriptor[168];')
 s=once(s,'put16(descriptor+20,0x1941);','put16(descriptor+20,0x2121);')
 s=once(s,'if(!packet(s,3,0,0,descriptor,24))return false;', '''memcpy(descriptor+24,r->used,144);
 if(!packet(s,3,0,0,descriptor,sizeof descriptor))return false;
 if(!nes_resident211_commit(r,s->serial,s->generation,r->target,true))return fail(s,5);''')
 f.write_text(s,encoding='utf8',newline='\n')
 f=out/'nes_sink_bulk195.inc';s=f.read_text();s=once(s,'offset/unit!=(kind?s->obj_next:s->bg_next)||','')
 # Counters now count transferred units, not a contiguous destination prefix.
 f.write_text(s,encoding='utf8',newline='\n')
 (out/'sink212-preparation.json').write_text(json.dumps(dict(inputs=pins,outputs={n:sha(out/n) for n in pins},production_runtime_connected=False),indent=2)+'\n',encoding='utf8')
