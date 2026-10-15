# SPDX-License-Identifier: MIT
"""Extract production186 metadata/slot planning, retaining checks and raw path.
The generated candidate does not materialize or stage BG/OBJ CHR bytes.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def prepare(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    src=ROOT.parent/'probes/nes-paired186/arm01/src/nes_native_video165.c'
    s=src.read_text();s=s[:s.index('\nbool nes_native_video165_build(')]+'\n'
    s=replace(s,'#include "nes_native_video165.h"','#include "nes_plan191.h"')
    s=replace(s,'nes_native_video185_build(', 'nes_native_video191_plan(')
    s=replace(s,'nes_native_video165_stage_fn stage','nes_plan191_fn plan')
    s=replace(s,'!p||!stage','!p||!plan')
    start=s.index(' /* Slot0 is already zero in OAM scratch.')
    end=s.index(' for(unsigned g=0;g<groups;g++)for(unsigned x=0;x<33;x++){',start)
    s=s[:start]+''' /* Slot0 is explicitly zero, without reading any CHR payload. */
 {struct nes_plan191 q={0};q.generation=s->generation;q.kind=2;
  for(unsigned f=0;f<8;f++)q.alt[f]=65535;
  if(!plan(ctx,&q))return fail(p,14);}
'''+s[end:]
    s=replace(s,'const uint8_t *src=tile(s,cell&8191,1);if(!src)return fail(p,6);','if(!tile(s,cell&8191,1))return fail(p,6);')
    s=replace(s,'uint8_t b[16],mapping[16];','struct nes_plan191 q={0};q.generation=s->generation;q.tag=(uint16_t)(cell&8191);q.mask=255;\n  for(unsigned f=0;f<8;f++)q.alt[f]=65535;\n  uint8_t *mapping=q.row;')
    s=replace(s,';b[f]=src[mapping[f]+((f&1)?8:0)];',';')
    s=replace(s,'const uint8_t *lo=tile(s,e>>19,1);if(!lo)return fail(p,6);','if(!tile(s,e>>19,1))return fail(p,6);')
    s=replace(s,'b[fine(s,y,0,false)*2]=lo[e&7];','q.alt[fine(s,y,0,false)]=(uint16_t)(e>>19);')
    s=replace(s,'''   memcpy(p->oam+(slot%15)*16,b,16);
   if(slot%15==14&&!stage(ctx,0,slot-14,p->oam,240))return fail(p,14);''',
      '   q.slot=(uint16_t)slot;if(!plan(ctx,&q))return fail(p,14);')
    s=replace(s,' if(p->bg_count%15&&!stage(ctx,0,p->bg_count-p->bg_count%15,p->oam,(p->bg_count%15)*16))return fail(p,14);','')
    s=replace(s,'const uint8_t *src=tile(s,tag,2);if(!src)return fail(p,9);','if(!tile(s,tag,2))return fail(p,9);')
    s=replace(s,'uint8_t b[32]={0};for(unsigned f=0;f<8;f++)if(masks[e]&(1u<<f)){b[f*2]=src[f];b[f*2+1]=src[f+8];}',
     '''struct nes_plan191 q={0};q.generation=s->generation;q.tag=(uint16_t)tag;q.kind=1;q.mask=masks[e];
   for(unsigned f=0;f<8;f++){q.row[f*2]=q.row[f*2+1]=(uint8_t)f;q.alt[f]=65535;}''')
    s=replace(s,'''    memcpy(p->cgram+(slot%7)*32,b,32);
    if(slot%7==6&&!stage(ctx,1,slot-6,p->cgram,224))return fail(p,14);''',
      '    q.slot=(uint16_t)slot;if(!plan(ctx,&q))return fail(p,14);')
    s=replace(s,' if(p->obj_count%7&&!stage(ctx,1,p->obj_count-p->obj_count%7,p->cgram,(p->obj_count%7)*32))return fail(p,14);','')
    assert 'stage(' not in s and '->data[' not in s and 'src[' not in s
    (out/'nes_plan191.c').write_text(s,encoding='utf8',newline='\n')
    (out/'nes_plan191.h').write_bytes((ROOT/'src/nes/firmware/nes_plan191.h').read_bytes())
    return dict(reference_sha256=sha(src),candidate_sha256=sha(out/'nes_plan191.c'))
