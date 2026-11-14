# SPDX-License-Identifier: MIT
"""Materialize the MMC763 slot-index, OBJ-first and sealed-refill experiments."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out, obj_first, refill=False):
    out.mkdir(parents=True, exist_ok=False)
    def save(name, source):
        (out/name).write_text(source, newline="\n")

    name="nes_planner211.c"
    assert sha(base/name)=="7493a16b67ca1d56f637de1a0813023a6786bbd3b2365bcc4d1ac5a50d6f2db7"
    s=(base/name).read_text()
    # The HDMA table is built after all BG rows; only current-frame slots
    # allocated by the normal validated path can populate the local index.
    s=once(s," unsigned next_offer=3;", """ uint8_t *slot_index=p->hdma;
 memset(slot_index,0,128);
 unsigned next_offer=3;""")
    s=once(s,"  }else{\n  if(!tile(s,cell&8191,1))", """  }else{
  unsigned tag=cell&8191,idx781=(tag&63)*2;
  slot=(unsigned)slot_index[idx781]|((unsigned)slot_index[idx781+1]<<8);
  if(!exceptional && slot && p->bg_keys[slot]==(tag|UINT64_C(0x1fed6c8da4480000)))goto have_slot781;
  if(!tile(s,cell&8191,1))""")
    s=once(s,"  if(slot>=1024)return fail(p,7);\n  }","""  if(slot>=1024)return fail(p,7);
  if(!exceptional)put16(slot_index+idx781,slot);
  }
have_slot781:""")
    # Expired index bytes must not leak into the canonical zero HDMA padding.
    s=once(s," unsigned at=0;"," memset(slot_index,0,128);\n unsigned at=0;")
    if obj_first:
        a=s.index(" /* No callback retains scratch pointers;")
        b=s.index(" /* CGRAM becomes",a)
        obj=s[a:b]
        c=obj.index(" /* BG allocation")
        e=obj.index(" memset(rank_used",c)
        obj=obj[:c]+""" /* CGRAM is unused until palette construction. It is independent of
  * BG keys, OBJ keys, and OAM, including when BG allocation follows. */
 uint8_t *rank_used=p->cgram,*evaluation=rank_used+224;
"""+obj[e:]
        # Run the same validation and rank-ordered OBJ builder once. Cold
        # follows the previous order. Keep BG and OBJ namespaces independent.
        fn="static bool objects781(const struct nes_native165 *s,struct nes_native_video165 *p,struct nes_resident211 *resident,unsigned palettes){\n"+obj+" return true;\n}\n"
        s=s[:a]+""" if(!early_obj && !objects781(s,p,resident,palettes))return false;
 if(early_obj && !resident->tile_boundary(resident->ctx,true))return fail(p,7);
"""+s[b:]
        s=once(s,"static bool build211(",fn+"static bool build211(")
        s=once(s," uint32_t reusable474=0;", """ bool early_obj=resident->tile_boundary!=NULL;
 if(early_obj){
  if(!objects781(s,p,resident,palettes) ||
     !resident->tile_boundary(resident->ctx,false))return fail(p,7);
 }
 uint32_t reusable474=0;""")
        h="nes_resident211.h"
        save(h,once((base/h).read_text()," uint8_t first_bg_rows;", " bool (*tile_boundary)(void *,bool);\n uint8_t first_bg_rows;"))
        n="nes_native_runtime165.c"
        runtime=once((base/n).read_text(),"static bool planner221(", """static bool tile_boundary781(void *ctx,bool end){
 struct nes_native_runtime165 *s=ctx;
 return end ? nes_plan200_end(&s->plan) : nes_plan549_first(&s->plan);
}
static bool planner221(""")
        runtime=once(runtime,"  if(!planner221(s))","  s->resident->tile_boundary=s->plan.bank_history==2?tile_boundary781:NULL;\n  if(!planner221(s))")
        runtime=once(runtime,"bool end_ok=nes_plan200_end(&s->plan);","bool end_ok=s->plan.ending || nes_plan200_end(&s->plan);")
        runtime=once(runtime," bool input_wait=reason<=1", """ /* END may now precede raw/OAM materialization. Input remains owned
  * until the checked resident preparation has released all source reads. */
 if(s->resident && s->resident->tile_boundary && !s->resident->prepared)
  return check(ctx);
 bool input_wait=reason<=1""")
        if refill:
            # After the existing seven-block burst, recheck the full E0 before
            # each additional D1. This read cannot confirm display or COMMIT.
            runtime=once(runtime," if(reason==4 || (s->prefetch_left", """ if(reason==2 && !progress && !s->prefetch_left &&
    r->state==NES_NATIVE165_RECEIVING && s->transport.last[0]==3 &&
    s->transport.sent!=s->transport.retired){
  s->prefetch_left=1;
 }
 if(reason==4 || (s->prefetch_left""")
        save(n,runtime)
    save(name,s)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("base",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--obj-first",action="store_true")
    p.add_argument("--refill",action="store_true")
    a=p.parse_args()
    if a.refill and not a.obj_first:
        p.error("--refill requires --obj-first")
    prepare(a.base,a.out,a.obj_first,a.refill)
