"""Test OAM issue order and distinguish tile completion from advisory map progress."""
import argparse
from unittest.mock import patch
import nes_tile842 as base
from nes_oam840 import watch
from nes_pair839 import once

OUT = base.section.PROBES / "nes-tail844"
MODES = ("control", "release", "oamfirst", "objdone")


def arm(mode):
    return base.section.ARM if mode == "control" else base.section.ARM.parent / ("link-844" + mode)


def prepare(mode):
    if mode == "control":
        raise ValueError("Control uses the existing unmodified full link")
    name = "nes_native_sink165.c"
    source = (base.section.ARM / "src" / name).read_text()
    # Keep the full plan completion barrier. The subsequent bounded E0 loop
    # only asks whether the receiver has independently progressed its map DMA.
    source = once(source, "  for(unsigned poll=0;poll<120;poll++){",
                  "  for(unsigned poll=0;!p->section841 && poll<120;poll++){")
    if mode == "oamfirst":
        anchor = " if(!span(s,3,0,p->cgram,512))return false;"
        source = once(source, anchor, " if(p->section841 && !oam227(s,p->oam))return false;\n"+anchor)
        source = once(source, " if(!oam227(s,p->oam))return false;",
                      " if(!p->section841 && !oam227(s,p->oam))return false;")
    dest = OUT / mode
    dest.mkdir(parents=True, exist_ok=True)
    if mode=="objdone":
        src=base.section.ARM/"src"
        planner="nes_planner211.c"
        plan=once((src/planner).read_text(),"if(p->scroll_issued && resident->finish_obj",
                  "if((p->section841 || p->scroll_issued) && resident->finish_obj")
        (dest/planner).write_text(plan,newline="\n")
        runtime="nes_native_runtime165.c"
        code=once((src/runtime).read_text()," return p->sent || !p->count", """ if(s->video->section841){
  if(!nes_plan200_end(p))return false;
  return nes_oam844(&s->sink,s->video->oam);
 }
 return p->sent || !p->count""")
        (dest/runtime).write_text(code,newline="\n")
        header="nes_native_sink165.h"
        decl="bool nes_oam844(struct nes_native_sink165 *,const uint8_t *);\n"
        (dest/header).write_text(once((src/header).read_text(),"bool nes_section841(",decl+"bool nes_section841("),newline="\n")
        source=once(source,"static bool oam227(","bool nes_oam844(")
        source=once(source," if(same&&s->displayed", " if(!p->section841&&same&&s->displayed")
        source=once(source," if(!oam227(s,p->oam))"," if(!p->section841 && !nes_oam844(s,p->oam))")
    (dest / name).write_text(source, newline="\n")


def run(mode, test, phase):
    tag = f"844{mode}{test}"
    with patch.object(base, "arm", arm):
        base.run(mode, phase, "refopening" if test=="opening" else test, tag=tag, on_attach=watch)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=MODES)
    p.add_argument("test",choices=("prepare","fixed","opening","stop","damage"))
    p.add_argument("phase",type=int,choices=(1,2),nargs="?",default=1)
    a=p.parse_args()
    if a.test=="prepare":
        prepare(a.mode)
    else:
        run(a.mode,a.test,a.phase)
