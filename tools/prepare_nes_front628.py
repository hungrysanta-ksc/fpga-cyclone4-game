# SPDX-License-Identifier: MIT
"""Reuse the existing guarded offer after all BG rows become immutable."""
import argparse
from pathlib import Path
from prepare_nes_tail627 import prepare
from nes_raw506 import once


def build(base,out,burst=False):
    prepare(base,out,'control')
    path=out/'src/nes_planner211.c'
    s=path.read_text()
    # Keep the original offer for frames that had no mid-BG opportunity.
    s=once(s,'if(next_offer==3 && resident->offer_map && !resident->offer_map(resident->ctx))return fail(p,7);','')
    if burst:
        # Reuse the current cursor. Stop on the first missed credit, and
        # charge the E8 check again before every subsequent map packet.
        rt=out/'src/nes_native_runtime165.c'
        code=once(rt.read_text(),'static bool quiet528','''static bool offer628(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 for(unsigned i=0;i<3;i++){
  unsigned before=s->sink.map_next&127;
  if(!offer527(ctx))return false;
  if((s->sink.map_next&127)==before || s->sink.map_next>=64)break;
 }
 return true;
}
static bool quiet528''')
        rt.write_bytes(once(code,'resident->offer_map=offer527;', 'resident->offer_map=offer527;resident->offer_frozen=offer628;').encode())
        header=out/'src/nes_resident211.h'
        header.write_bytes(once(header.read_text(),'bool (*offer_map)(void *);',
                                'bool (*offer_map)(void *);bool (*offer_frozen)(void *);').encode())
        offer='''if(resident->offer_frozen){
  if(!resident->offer_frozen(resident->ctx))return fail(p,7);
 }else if(next_offer==3 && resident->offer_map && !resident->offer_map(resident->ctx))return fail(p,7);'''
    else:
        offer='if(resident->offer_map && !resident->offer_map(resident->ctx))return fail(p,7);'
    s=once(s,'memset(p->oam,0,sizeof(p->oam));','memset(p->oam,0,sizeof(p->oam));\n '+offer)
    path.write_bytes(s.encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--burst',action='store_true')
    a=p.parse_args()
    build(a.base,a.out,a.burst)
