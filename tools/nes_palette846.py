"""Measure palette lifetime and overlap its checked packets with outstanding OBJ."""
import argparse
import json
from types import SimpleNamespace
from unittest.mock import patch

from check_nes_game478 import UC_HOOK_CODE
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
import nes_dma845 as previous
from nes_pair839 import once
from nes_oam840 import watch as oam_watch

base = previous.base
OUT = base.section.PROBES / "nes-palette846"
BASE = previous.ARM


def link(mode):
    return BASE if mode == "control" else BASE.parent / ("link-846" + mode + "02")


def prepare(mode):
    assert mode in ("compute","issue","first","safe","queued")
    src = BASE / "src"
    dest = OUT / ("patch-" + mode)
    dest.mkdir(parents=True,exist_ok=True)
    name = "nes_planner211.c"
    source = (src/name).read_text()
    begin = source.index(" /* CGRAM becomes the palette")
    end = source.index("\n if(!raw841(s,p))",begin)
    palette = source[begin:end]
    palette = palette.replace(" /* CGRAM becomes the palette only after the final OBJ ACK. */",
                              " /* Palette storage is disjoint from the plan and raw scratch.\n"
                              "  * Committed palette and patch_count are immutable before this callback. */")
    raw_colors = """ if(p->patch_count){
  for(unsigned c=0;c<64;c++)put16(p->cgram+(64+c)*2,lut[c]);
 }
"""
    source = once(source,raw_colors,"")
    source = source[:begin] + source[end:]
    source = once(source," if((p->section841 || p->scroll_issued) && resident->finish_obj",
                  palette+"\n"+raw_colors+" if((p->section841 || p->scroll_issued) && resident->finish_obj")
    (dest/name).write_text(source,newline="\n")
    if mode == "compute":
        return
    name = "nes_native_sink165.c"
    source = (src/name).read_text()
    source = once(source,"bool nes_oam844(","""bool nes_palette846(struct nes_native_sink165 *s,const uint8_t *b){
 return span(s,3,0,b,512);
}

bool nes_oam844(""")
    source = once(source," if(!span(s,3,0,p->cgram,512))return false;",
                  " if(!p->section841 && !nes_palette846(s,p->cgram))return false;")
    (dest/name).write_text(source,newline="\n")
    name = "nes_native_sink165.h"
    source = once((src/name).read_text(),"bool nes_oam844(",
                  "bool nes_palette846(struct nes_native_sink165 *,const uint8_t *);\nbool nes_oam844(")
    (dest/name).write_text(source,newline="\n")
    name = "nes_native_runtime165.c"
    source = once((src/name).read_text(),"return nes_oam844(&s->sink,s->video->oam);",
                  "return nes_oam844(&s->sink,s->video->oam) && nes_palette846(&s->sink,s->video->cgram);")
    if mode in ("first","safe","queued"):
        source = once(source,"nes_oam844(&s->sink,s->video->oam) && nes_palette846(&s->sink,s->video->cgram)",
                      "nes_palette846(&s->sink,s->video->cgram) && nes_oam844(&s->sink,s->video->oam)")
    if mode in ("safe","queued"):
        source = once(source,"bool input_wait=reason<=1 && s->plan.finished && !progress;",
                      "bool input_wait=reason<=1 && s->plan.finished && !progress && s->resident && s->resident->prepared;")
    (dest/name).write_text(source,newline="\n")
    if mode == "queued":
        name = "nes_sink_window184.c"
        source = once((src/name).read_text(),
                      "s->last[1]==3 && (s->last[0]==2 || s->last[0]==4)",
                      "(s->last[1]==3 || s->last[1]==4) && (s->last[0]==2 || s->last[0]==4 || (s->last[1]==4 && s->last[0]==8))")
        (dest/name).write_text(source,newline="\n")


def watch(cpu):
    oam_watch(cpu)
    region = cpu.video + cpu.layout["nes_native_video165"]["cgram"]
    writes = {}
    log = cpu.a.out / "palette846.jsonl"
    def stamp(kind, **kwargs):
        if cpu.generation not in (909,910):
            return
        row = dict(event=kind,g=cpu.generation,clock=cpu.clock,
                   last_store=writes.get(cpu.generation),**kwargs)
        with log.open("a") as stream:
            print(json.dumps(row),file=stream)
    def written(u,access,at,size,value,user):
        writes[cpu.generation] = cpu.clock
    cpu.u.hook_add(UC_HOOK_MEM_WRITE,written,begin=region,end=region+511)
    def wire(u,addr,size,user):
        op,section,offset = (u.reg_read(i) for i in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
        if section in (3,4) or op == 3:
            stamp("wire",op=op,section=section,offset=offset,
                  cgram=bytes(u.mem_read(region,512)).hex() if section == 3 else None)
    pc = cpu.syms["packet_wire"]
    cpu.u.hook_add(UC_HOOK_CODE,wire,begin=pc,end=pc)
    def enter(u,addr,size,name):
        stamp(name)
    for name in ("finish_obj810","nes_sink212_seal","nes_plan200_end"):
        pc = cpu.syms[name]
        cpu.u.hook_add(UC_HOOK_CODE,enter,name,begin=pc,end=pc)


def run(mode,test,phase,tag=None):
    # 837 from reset is the primary comparison. Fixed alone isolates the
    # later service with the previously measured 841 receiver.
    tag = tag or f"846{mode}{test}"
    with patch.object(base,"arm",link):
        if test == "boot":
            with patch.object(base.replay,"TraceLink",base.Trace):
                base.replay.run("palette",phase,base.TEMP,base.BUDGET,arm=link(mode),
                                client=base.section.REFERENCE,tag=tag,on_attach=watch)
        elif test in ("pulse","coverage"):
            import replay_nes_window837 as guard
            a = SimpleNamespace(fault=test,temp=base.TEMP,budget=base.BUDGET,phase=phase,arm="palette")
            guard.reject(a,base.section.REFERENCE,link(mode),tag)
        else:
            base.run(mode,phase,test,tag=tag,on_attach=watch)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("control","compute","issue","first","safe","queued"))
    p.add_argument("test",choices=("prepare","boot","fixed","refopening","stop","damage","pulse","coverage"))
    p.add_argument("phase",type=int,choices=(1,2),nargs="?",default=1)
    p.add_argument("--tag")
    a = p.parse_args()
    if a.test == "prepare":
        prepare(a.mode)
    else:
        run(a.mode,a.test,a.phase,a.tag)
