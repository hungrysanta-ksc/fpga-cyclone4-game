# SPDX-License-Identifier: MIT
"""Change the first map offer and the checked post-SEAL input service independently."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha

MODES = ("map", "input", "joint", "raster", "burst", "owner", "owner_burst", "owner_map", "owner_head", "owner_wait", "owner_retire", "owner_split")
BASE_ELF = "0b0d9c3907488f2cc94e888e5d7678af77f76fabe4d839f2dfbcea79454ccdeb"


def prepare(base, out, mode):
    assert sha(base / "obj-nes-100/sd2snes.elf") == BASE_ELF
    out.mkdir(parents=True, exist_ok=False)
    compact = mode.endswith("_fit")
    mode = mode.removesuffix("_fit")
    offer = mode in ("map", "joint", "owner_map", "owner_head", "owner_wait", "owner_split")
    burst = mode in ("input", "burst", "joint", "owner_burst")
    if offer or compact:
        name = "nes_native_sink165.c"
        source = (base / name).read_text()
        # Only the first offer after an owned OBJ can borrow the producer slot.
        # The next offer must re-enter ordinary progress. E1 still checks credit.
        if offer:
            source = once(source, "bool adjacent=pair && count==3;",
                """bool adjacent=pair && count==3;
  if(early==3 && s->deferred783 && s->plan->bulk_pending && s->plan->bulk[1] &&
     s->plan->window->sent==s->plan->bulk_until)adjacent=true;""")
        if mode in ("owner_head", "owner_wait", "owner_split"):
            # The previous E1 is an OBJ; one map changes last[] and consumes
            # this opportunity even if the old OBJ has already retired.
            source = once(source, "s->plan->bulk_pending && s->plan->bulk[1] &&\n     s->plan->window->sent==s->plan->bulk_until",
                          "s->plan->window->last[0]==7 && s->plan->window->last[1]==1")
        if compact:
            # The start of this run is in the left 32-row page and first<=27.
            source = once(source, "((mask>>first)&31)", "(((uint32_t)mask>>first)&31)")
        (out / name).write_text(source, newline="\n")
    if burst or mode.startswith("owner"):
        name = "nes_native_runtime165.c"
        source = (base / name).read_text()
        if mode.startswith("owner"):
            # Resident prepare has released source storage. An outstanding
            # checked bulk can service one input block at a no-progress wait.
            source = once(source, "reason<=1 && s->plan.finished", """reason<=1 &&
    (s->plan.finished || (!progress && s->resident && s->resident->prepared &&
                            s->plan.ending && s->plan.bulk_pending))""")
        if mode in ("owner_wait", "owner_retire", "owner_split"):
            # through() only reports reason 1 without progress while the
            # checked, non-SEAL target is still outstanding. Credit grant
            # (reason 0), completion and final ACK keep their old priority.
            source = once(source, "!progress && s->resident && s->resident->prepared &&\n                            s->plan.ending && s->plan.bulk_pending",
                          "reason==1 && s->resident && s->resident->prepared && s->plan.ending")
        if mode == "owner_split":
            source = once(source, """reason<=1 &&
    (s->plan.finished || (reason==1 && s->resident && s->resident->prepared && s->plan.ending)) && (!progress || reason==0)""",
                          """reason==0 ? s->plan.finished : reason==1 && !progress &&
    (s->plan.finished || (s->resident && s->resident->prepared && s->plan.ending))""")
        if burst:
            source = once(source, "  s->prefetch_left=1;",
                """  /* One E0 after up to three checked blocks once geometry is past
   * the map stage. STOP and the checked D2 confirmation remain per block. */
  s->prefetch_left=r->next_kind ? 3 : 1;""")
        (out / name).write_text(source, newline="\n")
    if mode in ("input", "raster", "joint"):
        name = "nes_native165.c"
        source = once((base / name).read_text(), """for(unsigned i=0;i<n;i++){
   if(!logical_record(s,4,gen,start+i,v))return false;
   v=raster_next471(v);
  }""", """if(!logical_record(s,4,gen,start,v))return false;
  uint64_t *next=s->raster+start+1;
  for(unsigned i=1;i<n;i++){v=raster_next471(v);*next++=v;}
  s->at[4]+=n-1;s->records+=n-1;""")
        (out / name).write_text(source, newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("mode", choices=MODES + tuple(m + "_fit" for m in MODES))
    args = parser.parse_args()
    prepare(args.base, args.out, args.mode)
