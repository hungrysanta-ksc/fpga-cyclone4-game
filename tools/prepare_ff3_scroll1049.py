"""Materialize the 1048 playable pair with a lower-cost ARM scrolling planner."""
import argparse
from pathlib import Path
from prepare_ff3_walk1048 import arm as arm1048
from prepare_nes_kirby1023 import edit


def arm(out):
    arm1048(out)
    src = out/'src'
    # The BG pass finishes before the first HDMA table is built or offered.
    # The planner's normal output reset already zeroes these bytes.
    edit(src, 'nes_planner211.c',
         ('uint32_t bg_lookup[64]={0};','_Static_assert(offsetof(struct nes_native_video165,hdma)%4==0,"aligned HDMA scratch");'),
         ('unsigned tag=cell&16383, cached=bg_lookup[tag&63];',
          'unsigned tag=cell&16383;uint32_t cached;uint8_t *entry=p->hdma+4*(tag&255);memcpy(&cached,entry,4);'),
         ('if(!((exceptional>>x)&1))bg_lookup[tag&63]=((tag+1)<<16)|slot;',
          'if(!((exceptional>>x)&1)){cached=((tag+1)<<16)|slot;memcpy(entry,&cached,4);}'))
    edit(src, 'nes_planner211.c',
         ('if(backdrop_used)for(unsigned x=', 'unsigned prior_fine=8;\n if(backdrop_used)for(unsigned x='),
         ('p->hofs[y]=0;p->vofs[y]', 'prior_fine=8;p->hofs[y]=0;p->vofs[y]'),
         ('bool split=y==0||fy==0||patched(s,y-1)||backdrop1046(s,y-1);\n  if(!split)split=split||fy!=fine(s,y-1,0,false)+1||e!=epoch(s,y-1)||',
          'bool split=fy!=prior_fine+1||e!=bank[groups-1]||'),
         ('if(split){if(groups==', 'prior_fine=fy;\n  if(split){if(groups=='))
    edit(src, 'nes_plan191.h', ('typedef bool (*nes_plan191_fn)', '''
extern const struct nes_plan191 nes_identity_plan;
typedef bool (*nes_plan191_fn)'''))
    edit(src, 'nes_planner211.c',
         ('static void map_word185', '''const struct nes_plan191 nes_identity_plan={
 .mask=255,.row={0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7},
 .alt={65535,65535,65535,65535,65535,65535,65535,65535}
};
static void map_word185'''),
         (''' if(p->map[at]!=(uint8_t)word||p->map[at+1]!=(uint8_t)(word>>8))p->map_dirty|=UINT64_C(1)<<(at/64);
 p->map[at]=(uint8_t)word;p->map[at+1]=(uint8_t)(word>>8);''',
          ''' uint16_t prev,value=(uint16_t)word;
 memcpy(&prev,p->map+at,sizeof prev);
 if(prev!=value){
  memcpy(p->map+at,&value,sizeof value);
  p->map_dirty|=UINT64_C(1)<<(at/64);
 }'''),
         ('''struct nes_plan191 q;q.generation=s->generation;q.slot=0;q.tag=(uint16_t)(cell&16383);q.kind=0;q.mask=255;
  for(unsigned f=0;f<8;f++)q.alt[f]=65535;
  uint8_t *mapping=q.row;for(unsigned f=0;f<8;f++){mapping[f*2]=(uint8_t)f;mapping[f*2+1]=(uint8_t)f;}''',
          '''struct nes_plan191 q=nes_identity_plan;q.generation=s->generation;q.tag=(uint16_t)tag;
  uint8_t *mapping=q.row;'''),
         ('''struct nes_plan191 q;q.generation=s->generation;q.slot=0;q.tag=(uint16_t)tag;q.kind=1;q.mask=masks[e];
   for(unsigned f=0;f<8;f++){q.row[f*2]=q.row[f*2+1]=(uint8_t)f;q.alt[f]=65535;}''',
          '''struct nes_plan191 q=nes_identity_plan;q.generation=s->generation;q.tag=(uint16_t)tag;q.kind=1;q.mask=masks[e];'''),
         ('{struct nes_plan191 q={0};q.generation=s->generation;q.kind=2;\n  for(unsigned f=0;f<8;f++)q.alt[f]=65535;',
          '{struct nes_plan191 q={0};q.generation=s->generation;q.kind=2;memset(q.alt,255,sizeof q.alt);'))
    edit(src, 'nes_resident211.c',
         (''' for(unsigned i=0;i<8;i++)if(q->alt[i]!=UINT16_MAX)return false;
 for(unsigned i=0;i<16;i++)if(q->row[i]!=i/2)return false;
 return true;''',''' return !memcmp(q->row,nes_identity_plan.row,sizeof q->row) &&
        !memcmp(q->alt,nes_identity_plan.alt,sizeof q->alt);'''))
    for name in ('nes_menu_diagnostic.c','nes_checkpoint112.c'):
        edit(src,name,('ff31048','ff31049'))


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    arm(ap.parse_args().out)
