# SPDX-License-Identifier: MIT
"""Generate a bounded geometry/H2, raw admission, group-step planner candidate.

The source is the pinned285 planner. Scratch keys are written before lookup;
only live output fields are cleared. No independent receiver check is removed.
"""
from nes_delta231 import once


def patch(s):
    header=s[:s.index('static bool build211(')]
    body=s[s.index(' if(!s||!lut||!p||!resident)'):s.index('\n p->valid=true;return true;')]
    validation=body[:body.index(' /* Validate captured material first')]
    validation=validation.replace(' if(!s||!lut||!p||!resident)return false;',' if(!s||!lut||!p||!resident||ctx286.phase)return false;')
    validation=validation.replace('NES_NATIVE165_COMMITTED','NES_NATIVE165_PREPARED')
    validation=validation.replace(' uint16_t base=inherit?p->generation:0;','')
    validation=validation.replace('   const uint8_t *pixels=nes_native181_pixels(s,raw_count++);if(!pixels)return fail(p,15);\n   for(unsigned x=0;x<256;x++)if(pixels[x]>=64)return fail(p,15);','   raw_count++;')
    grouping=body[body.index(' /* Regroup compact rows'):body.index(' p->groups=(uint8_t)groups;p->bg_count=1;')]
    grouping=grouping.replace(' uint8_t first[32],end[32],bank[32];unsigned groups=0;',' uint8_t *first=ctx286.first,*end=ctx286.end,*bank=ctx286.bank;unsigned groups=0;')
    grouping=once(grouping,'memcmp(&s->maps[g*33],&s->maps[(s->rows[y-1]>>3)*33],66)!=0',
                  '(g!=(s->rows[y-1]>>3)&&memcmp(&s->maps[g*33],&s->maps[(s->rows[y-1]>>3)*33],66)!=0)')
    zstart=body.index(' /* Slot0 is explicitly zero')
    gstart=body.index(' for(unsigned g=0;g<groups;g++){',zstart)
    gend=body.index(' } /* compact groups */',gstart)
    zero=body[zstart:gstart]
    group=body[gstart+len(' for(unsigned g=0;g<groups;g++){'):gend]
    template='''  struct nes_plan191 q={0};q.generation=s->generation;q.mask=255;
  for(unsigned f=0;f<8;f++)q.alt[f]=65535;
  uint8_t *mapping=q.row;for(unsigned f=0;f<8;f++){mapping[f*2]=(uint8_t)f;mapping[f*2+1]=(uint8_t)f;}
  bool shaped286=false;
'''
    group=once(group,'  for(unsigned x=0;x<33;x++){',template+'  for(unsigned x=0;x<33;x++){')
    a=group.index('  struct nes_plan191 q={0};q.generation=s->generation;q.tag=');b=group.index('  uint64_t key=',a)
    group=group[:a]+'''  q.tag=(uint16_t)(cell&8191);
  if(shaped286){for(unsigned f=0;f<8;f++){q.alt[f]=65535;mapping[f*2]=(uint8_t)f;mapping[f*2+1]=(uint8_t)f;}}
  shaped286=((exceptional>>x)&1)!=0;
'''+group[b:]
    finish=body[gend+len(' } /* compact groups */'):]
    # H2 scroll geometry is prepared before raw admission, so do not rebuild it.
    a=finish.index(' unsigned at=0;\n for(unsigned y=0;y<224;)');b=finish.index(' if(p->patch_count){',a)
    scroll=' memset(p->hdma,0,sizeof p->hdma);\n'+finish[a:b];finish=finish[:a]+finish[b:]
    # The constant color bias contributes plane6=1 and plane7=0. Transpose six
    # variable bits together instead of reloading a raw pixel eight times.
    a=finish.index('  for(unsigned slot=0;slot<p->patch_count;slot++){')
    b=finish.index('  for(unsigned c=0;c<64;c++)',a)
    finish=finish[:a]+'''  for(unsigned slot=0;slot<p->patch_count;slot++){
   const uint8_t *pixels=nes_native181_pixels(s,slot);
   for(unsigned x=0;x<256;x+=8){
    uint8_t a=0,b=0,c=0,d=0,e=0,f=0;
    for(unsigned j=0;j<8;j++){unsigned v=pixels[x+j];
     a=(uint8_t)((a<<1)|(v&1));b=(uint8_t)((b<<1)|((v>>1)&1));
     c=(uint8_t)((c<<1)|((v>>2)&1));d=(uint8_t)((d<<1)|((v>>3)&1));
     e=(uint8_t)((e<<1)|((v>>4)&1));f=(uint8_t)((f<<1)|((v>>5)&1));}
    uint8_t *q=p->patch.chr+(x/8)*64+slot*2;
    q[0]=a;q[1]=b;q[16]=c;q[17]=d;q[32]=e;q[33]=f;q[48]=255;
   }
  }
'''+finish[b:]
    return header+'''
struct context286 {
 const struct nes_native165 *s;const uint16_t *lut;
 struct nes_native_video165 *p;struct nes_resident211 *resident;struct nes_dirty231 *d;
 uint8_t first[32],end[32],bank[32],groups,g,palettes,phase;
 uint16_t generation;
};
static struct context286 ctx286;
unsigned context_size286(void){return sizeof ctx286;}
void cancel286(void){
 if(ctx286.phase){nes_resident211_abort(ctx286.resident);nes_dirty231_abort(ctx286.d);ctx286.p->valid=false;}
 ctx286.phase=0;
}
bool geometry286(const struct nes_native165 *s,const uint16_t *lut,struct nes_native_video165 *p,
                 struct nes_resident211 *resident,struct nes_dirty231 *d){
 bool inherit=resident->displayed;
'''+validation+grouping+scroll+'''
 ctx286.s=s;ctx286.lut=lut;ctx286.p=p;ctx286.resident=resident;ctx286.d=d;
 ctx286.groups=(uint8_t)groups;ctx286.g=0;ctx286.palettes=(uint8_t)palettes;
 ctx286.generation=s->generation;ctx286.phase=1;return true;
}
bool start286(void){
 const struct nes_native165 *s=ctx286.s;struct nes_native_video165 *p=ctx286.p;
 struct nes_resident211 *resident=ctx286.resident;struct nes_dirty231 *d=ctx286.d;
 if(ctx286.phase!=1||s->state!=NES_NATIVE165_COMMITTED||s->generation!=ctx286.generation)return false;
 for(unsigned i=0;i<s->patch_count*256u;i++)if(s->raw_pixels[i]>=64){cancel286();return false;}
 if(!nes_dirty231_begin(d,resident)||!nes_dirty231_material(d,s,ctx286.lut,p)){cancel286();return false;}
 bool inherit=resident->displayed;uint16_t base=inherit?p->generation:0;
 /* Exact-key arrays are read only for used slots, after their first write.
  * Preserve geometry/H2 fields already prepared; final output arrays have
  * their own complete clears below. Do not erase retained raw comparison. */
 if(!inherit)memset(p->map,0,sizeof p->map);
 p->map_dirty=inherit?0:UINT64_MAX;p->map_inherit=inherit;p->map_base_generation=base;p->generation=s->generation;
 p->bg_count=1;p->obj_count=0;p->objects=0;p->error=0;p->valid=false;p->groups=ctx286.groups;
'''+zero+'''
 ctx286.phase=2;return true;
}
/* 0=fault,1=one group completed,2=whole tentative plan prepared. */
unsigned step286(void){
 if(ctx286.phase!=2)return 0;
 const struct nes_native165 *s=ctx286.s;const uint16_t *lut=ctx286.lut;
 struct nes_native_video165 *p=ctx286.p;struct nes_resident211 *resident=ctx286.resident;struct nes_dirty231 *d=ctx286.d;
 unsigned palettes=ctx286.palettes;
 if(s->state!=NES_NATIVE165_COMMITTED||s->generation!=ctx286.generation){cancel286();return 0;}
 if(ctx286.g<ctx286.groups){
  unsigned g=ctx286.g++;uint8_t *first=ctx286.first,*end=ctx286.end,*bank=ctx286.bank;
'''+group+'''
  return 1;
 }
'''+finish+'''
 p->valid=true;
 if(!nes_resident211_prepare(resident,p->map_dirty)){cancel286();return 0;}
 d->prepared=true;d->raw=p->patch_count!=0;ctx286.phase=0;return 2;
}
'''
