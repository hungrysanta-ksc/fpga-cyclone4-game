"""Retain MMC855 packet-header timing while keeping the two section-5 submissions."""
import argparse
from nes_raw506 import once
from prepare_nes_trial802 import PROBES


def prepare(variant):
    name='nes_native_sink165.c'
    text=(PROBES/'nes-tail864/link/src'/name).read_text()
    text=once(text,'memcpy(b+4,&s->serial,4);',
              'for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s->serial>>(i*8));')
    if variant in ('pairs','coverage','credit','empty','cursor','suffix','skip','offer','span'):
        # All raw rows contain two adjacent bitplane bytes per tile. Preserve
        # the original order and C alignment rules with a fixed-size copy.
        text=once(text,'for(unsigned bit=0;bit<2;bit++)out[packed++]=p->patch.chr[tile*64+plane*16+row*2+bit];',
                  '{memcpy(out+packed,p->patch.chr+tile*64+plane*16+row*2,2);packed+=2;}')
        text=once(text,'memcpy(descriptor,size,sizeof size);',
                  'for(unsigned i=0;i<6;i++)put16(descriptor+i*2,size[i]);')
    if variant in ('coverage','empty','cursor','span'):
        old='for(unsigned i=0;i<144;i++)if(r->used[i]&~(r->resident[r->target][i]|r->dirty[i]))return fail(s,5);'
        text=once(text,old,'''for(unsigned i=0;i<sizeof r->used;i+=4){
  uint32_t used,resident,dirty;
  memcpy(&used,r->used+i,4);
  memcpy(&resident,r->resident[r->target]+i,4);
  memcpy(&dirty,r->dirty+i,4);
  if(used&~(resident|dirty))return fail(s,5);
 }
 _Static_assert(sizeof r->used==144 && sizeof r->dirty==144 &&
                sizeof r->resident[0]==144,"coverage width");''')
    if variant=='empty':
        point='bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,unsigned early){'
        text=once(text,point,point+'''
 /* No run can be offered or paired. The normal empty scan only clears
  * this hint; it leaves the cursor, token and credit window alone. */
 if(!mask){s->map_pair683=false;return true;}''')
    if variant in ('cursor','skip'):
        point='s->map_pair683=false;\n for(unsigned g=s->map_next&127;g<64;)'
        text=once(text,point,'''s->map_pair683=false;
 /* Nothing to publish; retain the cursor for the next planner offer. */
 if(!mask)return true;
 for(unsigned g=s->map_next&127;g<64;)''')
    if variant=='suffix':
        point='if(!((mask>>g)&1)){g++;pair=false;continue;}'
        text=once(text,point,'''uint64_t remaining=mask>>g;
  if(!remaining)break;
  if(!(remaining&1)){g+=(unsigned)__builtin_ctzll(remaining);pair=false;}''')
    if variant=='span':
        # A repeat needs 64 bytes before span_piece can introduce a boundary.
        # At exactly 64 the only possible piece is still the entire interval.
        text=once(text,'bool split=span_cost227(b,n)&1;',
                  'bool split=n>64 && (span_cost227(b,n)&1);')
        start=' unsigned cost=(first?(span_cost227(b,first)>>1):0)+471+8*4+(span_cost227(b+512,32)>>1);'
        text=once(text,start+'\n if(length<64||repeat_bytes(b+first,length)==length||cost>=(span_cost227(b,544)>>1))',
                  ' if(length<64||repeat_bytes(b+first,length)==length)return span(s,4,0,b,544);\n'+start+
                  '\n if(cost>=(span_cost227(b,544)>>1))')
    out=PROBES/'nes-opening865'/('patch-'+variant)
    out.mkdir(parents=True,exist_ok=True)
    if variant=='offer':
        mask='r->map_stale[r->target]|p->map_dirty'
        text=once(text,'if(s->map_next>=64)return true;\n if(!final){','''if(s->map_next>=64)return true;
 uint64_t mask='''+mask+''';
 if(!final){
  if(!mask && !s->plan->bulk_pending){
   s->map_pair683=false;
   return nes_plan200_valid(s->plan)||fail(s,5);
  }''')
        text=once(text,'return map527(s,p,'+mask+',final?2:1);','return map527(s,p,mask,final?2:1);')
        src=PROBES/'nes-trial855/link/src'
        plan=(src/'nes_plan_service200.c').read_text()
        plan=once(plan,'static bool valid(struct nes_plan200 *p)','bool nes_plan200_valid(struct nes_plan200 *p)')
        plan=plan.replace('valid(p)','nes_plan200_valid(p)')
        (out/'nes_plan_service200.c').write_text(plan,newline='\n')
        hdr=(src/'nes_plan_service200.h').read_text()
        hdr=once(hdr,'bool nes_plan527_map_credit','bool nes_plan200_valid(struct nes_plan200 *);\nbool nes_plan527_map_credit')
        (out/'nes_plan_service200.h').write_text(hdr,newline='\n')
    (out/name).write_text(text,newline='\n')
    if variant=='credit':
        name='nes_plan_service200.c'
        plan=(PROBES/'nes-trial855/link/src'/name).read_text()
        point='uint8_t flags;\n for(unsigned i=0;i<p->poll_limit;i++){\n  if(!poll(p,&flags,NES_PLAN215_FINISH))'
        plan=once(plan,point,'''/* A checked palette/OAM reuse can follow a pending tile. Collect that
  * tile's real credit before sampling the producer for its successor. */
 if(p->bulk_pending && p->window->last[0]==9 && p->window->last[1]==4 &&
    !complete485(p))return false;
 '''+point)
        (out/name).write_text(plan,newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant',choices=('header','pairs','coverage','credit','empty','cursor','suffix','skip','offer','span'))
    prepare(parser.parse_args().variant)
