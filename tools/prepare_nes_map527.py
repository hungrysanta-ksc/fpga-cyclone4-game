# SPDX-License-Identifier: MIT
"""Publish at most the first immutable map packet when the first dirty OBJ plan has been offered."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once,sha

ROOT=Path(__file__).resolve().parents[1]


def prepare(src,out,frontier=False):
    pin=json.loads((ROOT/'analysis/order520-verification.json').read_text())['guards']['blobs']['candidate']['sha256']
    assert sha(src/'obj-nes-100/firmware.stm')==pin
    out.mkdir(parents=True,exist_ok=False)
    def write(name,pairs):
        s=(src/name).read_text()
        for old,new in pairs:s=once(s,old,new)
        (out/name).write_text(s,newline='\n')
    write('nes_native_sink165.h',[('uint8_t state,error;bool displayed;','uint8_t state,error;bool displayed;uint8_t map_next;'),
        ('bool nes_sink212_seal(', 'bool nes_sink527_early(struct nes_native_sink165 *,struct nes_native_video165 *,struct nes_resident211 *);\nbool nes_sink212_seal(')])
    write('nes_plan_service200.h',[('bool nes_plan200_end(', 'bool nes_plan527_map_credit(struct nes_plan200 *,bool *);\nbool nes_plan200_end(')])
    write('nes_plan_service200.c',[('static bool flush(','''bool nes_plan527_map_credit(struct nes_plan200 *p,bool *ready){
 uint8_t flags;
 *ready=false;
 if((uint16_t)(p->window->sent-p->window->retired)>=3)return true;
 if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;
 /* A ready tile owns this opportunity. Leave at least one queue slot free. */
 *ready=!(flags&4);
 return true;
}
static bool flush(''')])
    s=(src/'nes_native_sink165.c').read_text()
    start=s.index(' for(unsigned g=0;g<64;)')
    end=s.index(' for(unsigned k=3;k<6;',start)
    loop=s[start:end].replace('unsigned g=0','unsigned g=s->map_next&127').replace('r->map_upload','mask')
    loop=once(loop,'packet(s,2,2,','packet(s,early?24:2,2,')
    loop=once(loop,'count*64))return false;','count*64))return false;\n  if(early){s->map_next=(uint8_t)g;break;}')
    helper='''static bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,bool early){
'''+loop+''' return true;
}
bool nes_sink527_early(struct nes_native_sink165 *s,struct nes_native_video165 *p,struct nes_resident211 *r){
 if(s->map_next)return true;
 s->map_next=128; /* Tried once. Low seven bits count rows preceding the suffix. */
 bool ready;
 if(!nes_plan527_map_credit(s->plan,&ready))return false;
 return !ready||map527(s,p,r->map_stale[r->target]|p->map_dirty,true);
}
'''
    s=s[:start]+' if(!map527(s,p,r->map_upload,false))return false;\n'+s[end:]
    s=once(s,'bool nes_sink212_seal(',helper+'bool nes_sink212_seal(')
    s=once(s,'op!=23 &&','op!=23 && op!=24 &&')
    s=once(s,'bool bulk_submit=op==23;', 'if(op==24)op=2; /* Internal, pre-arbitrated map. Normal DATA/RLE wire ABI. */\n bool bulk_submit=op==23;')
    s=once(s,'s->sequence=0;s->bg_next','s->map_next=0;s->sequence=0;s->bg_next')
    (out/'nes_native_sink165.c').write_text(s,newline='\n')
    write('nes_native_runtime165.c',[('if(!ok)return false;\n nes_budget210_plan(q);',
        '''if(!ok)return false;
 /* OBJ allocation begins after every BG map write. Keep the first BG flush
  * and the current plan submission ahead of this speculative map packet. */
 if(q->kind==1 && !nes_sink527_early(&s->sink,s->video,s->resident))return false;
 nes_budget210_plan(q);''')])
    if frontier:
        write('nes_resident211.h',[('uint64_t map_stale[2],map_upload;',
            'bool (*offer_map)(void *);uint64_t map_stale[2],map_upload;')])
        name='nes_native_runtime165.c'
        runtime=(out/name).read_text()
        begin=runtime.index(' /* OBJ allocation begins')
        end=runtime.index(' nes_budget210_plan(q);',begin)
        runtime=runtime[:begin]+runtime[end:]
        runtime=once(runtime,'static bool planner221(','''static bool offer527(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 return nes_sink527_early(&s->sink,s->video,s->resident);
}
static bool planner221(''')
        runtime=once(runtime,'nes_resident211_reset(resident);','nes_resident211_reset(resident);resident->offer_map=offer527;')
        (out/name).write_text(runtime,newline='\n')
        name='nes_planner211.c'
        planner=(src/name).read_text()
        marker='for(unsigned g=0;g<groups;g++){\n  nes_cost474_groups++;'
        planner=once(planner,marker,'''bool offered=false;
 for(unsigned g=0;g<groups;g++){
  /* Physical rows g and g+32 are the only map destinations of this group.
   * At entry the preceding three left-page rows and all lower rows are
   * final, including the values retained from the last display. Therefore
   * the original ascending, up-to-three-row packet cannot change later. */
  if(resident->offer_map && !offered && g>=3 &&
     ((resident->map_stale[resident->target]|p->map_dirty) & (UINT64_C(1)<<(g-3)))){
   offered=true;if(!resident->offer_map(resident->ctx))return fail(p,7);
  }
  nes_cost474_groups++;''')
        planner=once(planner,' } /* compact groups */',''' } /* compact groups */
 if(!offered && resident->offer_map && !resident->offer_map(resident->ctx))return fail(p,7);''')
        (out/name).write_text(planner,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--frontier',action='store_true')
    a=p.parse_args();prepare(a.arm,a.out,a.frontier)
