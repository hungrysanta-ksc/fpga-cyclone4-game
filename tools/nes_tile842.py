"""Time the zero BG and OBJ plan with the normal producer, bulk queue and PPU."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

import replay_nes_section832 as replay
import nes_section841 as section
from nes_pair839 import once

OUT = section.PROBES / "nes-tile842"
TEMP = Path.home() / "AppData/Local/Temp"
BUDGET = Path.home() / "Downloads/nes-budget-mmc826.txt"
CLIENT = section.OUT / "client-paired-stop"


def arm(mode):
    return section.ARM if mode == "control" else section.ARM.parent / ("link-842" + mode)


def prepare(mode):
    dest = OUT / ("patch-" + mode)
    dest.mkdir(exist_ok=True, parents=True)
    src = section.ARM / "src"
    name = "nes_planner211.c"
    code = (src / name).read_text()
    a = code.index(" /* No callback retains scratch")
    b = code.index(" if(p->scroll_issued", a)
    objects = code[a:b]
    start = code.index(" /* Slot0 is explicitly")
    end = code.index(" /*226:", start)
    zero = code[start:end]
    code = code[:a] + " if(!early842 && !objects842(s,p,resident,palettes))return false;\n" + code[b:]
    code = code[:start] + code[end:]
    # rank/evaluation may use the high end of bg_keys before BG allocation.
    # Slot zero occupies its first eight bytes. After BG allocation all keys expire.
    objects = once(objects, "(uint8_t *)p->bg_keys,", "(uint8_t *)(p->bg_keys+968),")
    late = mode == "after6"
    delayed = mode in ("defer1","credit1","credit6","drain6")
    prefix = mode in ("prefix1","prefix6") or late or delayed
    if prefix:
        objects = once(objects, "   unsigned o=p->objects++", """   if(limit){
    if(resident->writes-initial>=limit)return true;
    continue;
   }
   unsigned o=p->objects++""")
        objects = " unsigned initial=resident->writes;\n" + objects
    helper = ("static bool objects842(const struct nes_native165 *s,struct nes_native_video165 *p,"
              "struct nes_resident211 *resident,unsigned palettes" + (",unsigned limit" if prefix else "")+
              "){\n" + objects + " return true;\n}\n")
    code = once(code, "static bool build211(", helper + "static bool build211(")
    code = once(code, " if(resident->displayed && resident->early_section", zero +
                " bool early842=resident->displayed && resident->early_section")
    code = once(code, "==0x7ffffu)){\n  scroll841(p);",
                "==0x7ffffu);\n if(early842){\n  if(!objects842(s,p,resident,palettes))return false;\n  scroll841(p);")
    if prefix:
        code = once(code,"if(!objects842(s,p,resident,palettes))","if(!objects842(s,p,resident,palettes,"+mode[-1]+"))")
        code = once(code,"if(!early842 && !objects842(s,p,resident,palettes))","if(!objects842(s,p,resident,palettes,0))")
    if late:
        code = once(code,"  if(!objects842(s,p,resident,palettes,6))return false;\n","")
        code = once(code,"  p->hdma_size=0;","""  p->hdma_size=0;
  if(!objects842(s,p,resident,palettes,6) || !resident->finish_obj ||
     !resident->finish_obj(resident->ctx))return fail(p,7);""")
        name2 = "nes_native_runtime165.c"
        runtime=once((src/name2).read_text()," return p->sent || !p->count", """ if(s->video->section841 && !s->video->scroll_issued){
  bool room;
  return nes_plan549_first(p) && nes_plan527_map_credit(p,&room);
 }
 return p->sent || !p->count""")
        (dest/name2).write_text(runtime,newline="\n")
    # raw841 and its cleanup overlap the zero slot's scratch word, whose exact key is zero.
    (dest/name).write_text(code, newline="\n")
    name = "nes_native_sink165.c"
    code = (src/name).read_text()
    code = once(code, "s->plan->started || s->plan->bulk_pending || !n",
                "s->plan->ending || !n")
    pos = " if(!(n&1))p->hdma[n++]=0;"
    start = code.index("bool nes_section841(")
    tail = code[start:] if late else once(code[start:], pos, " if(!nes_plan549_first(s->plan))return false;\n" + pos)
    if mode == "service":
        tail = once(tail, " if(!packet(s,24,5,0,p->hdma,n)", " bool room;\n if(!nes_plan527_map_credit(s->plan,&room) || !packet(s,24,5,0,p->hdma,n)")
        tail = once(tail, "words,10) || !packet(s,24,5,1505", "words,10) || !nes_plan527_map_credit(s->plan,&room) || !packet(s,24,5,1505")
    if delayed:
        refresh = (" uint8_t ack[12];\n if(!nes_window184_drain(s->plan->window,ack))return false;\n"
                   if mode.startswith("credit") or mode=="drain6" else "")
        tail = once(tail," p->section841=true;", refresh + """ bool room;
 if(!nes_plan527_map_credit(s->plan,&room))return false;
 p->section841=true;""")
        if mode=="drain6":
            tail=once(tail," bool room;\n if(!nes_plan527_map_credit(s->plan,&room))return false;",
                      " if(!nes_plan842_ready(s->plan))return false;")
            for filename,anchor,addition in (
                ("nes_plan_service200.h","bool nes_plan527_map_credit","bool nes_plan842_ready(struct nes_plan200 *p);\n"),
                ("nes_plan_service200.c","bool nes_plan527_map_credit","""bool nes_plan842_ready(struct nes_plan200 *p){
 for(unsigned i=0;i<5;i++){
  uint8_t flags;
  if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;
  if(!(flags&4) || !p->bulk_pending)break;
  if(!complete485(p))return false;
 }
 return true;
}
""")):
                (dest/filename).write_text(once((src/filename).read_text(),anchor,addition+anchor),newline="\n")
    if prefix and not late and not delayed:
        tail = once(tail," if(!packet(s,24,5,0,p->hdma,n)"," bool room;\n if(!nes_plan527_map_credit(s->plan,&room) || !packet(s,24,5,0,p->hdma,n)")
        tail = once(tail,"words,10) || !packet(s,24,5,1505","words,10) || !nes_plan842_return(s->plan) || !packet(s,24,5,1505")
        for filename,anchor,replacement in (
            ("nes_plan_service200.c","static uint32_t token485","bool nes_plan842_return(struct nes_plan200 *p){return complete485(p);}\nstatic uint32_t token485"),
            ("nes_plan_service200.h","bool nes_plan527_map_credit","bool nes_plan842_return(struct nes_plan200 *p);\nbool nes_plan527_map_credit")):
            (dest/filename).write_text(once((src/filename).read_text(),anchor,replacement),newline="\n")
    (dest/name).write_text(code[:start] + tail, newline="\n")


class Trace(replay.TraceLink):
    def __init__(self, args):
        super().__init__(args)
        self.details = []
        select = self.calendar.select

        def measured(request):
            grant, response = select(request)
            if self.generation == 910:
                self.details.append(["grant", self.record, request+self.a.rom_phase,
                                     grant+self.a.rom_phase, response+self.a.rom_phase])
            return grant, response
        self.calendar.select = measured

    def decode557(self, q, arrived, now):
        start = super().decode557(q, arrived, now)
        if start <= now and self.generation == 910:
            self.record = [q[6], int.from_bytes(q[2:4], "little")]
            self.details.append(["decode", self.record, arrived, start])
        return start

    def exchange(self, seq, t, op, args):
        if op == "FINISH":
            (self.a.out/"plan842.json").write_text(json.dumps(self.details))
        return super().exchange(seq, t, op, args)


def run(mode, phase, test, *, tag=None, on_attach=None):
    tag = tag or "842" + mode + test
    if test in ("opening","refopening"):
        client = CLIENT if test=="opening" else section.REFERENCE
        with patch.object(sys,"argv",["replay","","","","","",tag,str(BUDGET)]):
            section.main(section.PROBES/"nes-tile821/extra01","earlyB","jointmirror",phase,TEMP,
                         arm=arm(mode)/"src", link_class=section.MirrorLink,client=client,
                         client_hash=section.sha(client/"sink165.sfc"))
        return
    fixed = test in ("fixed","stop","damage")
    def adapt(lua):
        if fixed:
            old = (section.REFERENCE/"body.bin").read_bytes()
            new = (CLIENT/"body.bin").read_bytes()
            writes = [f"emu.write({8192+i},{v},emu.memType.snesWorkRam)"
                      for i,v in enumerate(new) if i >= len(old) or v != old[i]]
            lua = once(lua, "  lastStatus=ack[1];", "  if pw(8)==909 and pb(0)==3 and ack[1]==1 then\n"
                       + "\n".join(writes) + "\n  end\n  lastStatus=ack[1];")
        if test != "original":
            with patch.object(section.pair, "CLIENT", CLIENT):
                lua = section.pair.oracle(lua)
            return section.observe_raw(lua, CLIENT, test=="stop", test=="damage")
        return lua
    with patch.object(replay, "TraceLink", Trace):
        try:
            replay.run("palette", phase, TEMP, BUDGET, arm=section.BASE if test=="original" else arm(mode),
                       client=section.REFERENCE if fixed or test=="original" else CLIENT, tag=tag, adapt=adapt, on_attach=on_attach)
        except (AssertionError,OSError,TimeoutError):
            if test not in ("stop","damage"):
                raise
            folder = TEMP/f"nes-tile821-demoB-jointmirror-p{phase}-{tag}"
            tick = int((folder/"stop841.txt").read_text())
            assert int((folder/"cancel841.txt").read_text()) >= tick
            rows = section.window(folder)
            assert [r["g"] for r in rows if r["event"]=="reveal"] == list(range(905,910))
            assert not any(r["event"] in ("ppu_dma","ppu_last","reveal") and r["clock"]>=tick for r in rows)
        else:
            assert test not in ("stop","damage")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("control","early","service","prefix1","prefix6","after6","defer1","credit1","credit6","drain6"))
    parser.add_argument("test", choices=("prepare","original","fixed","static","opening","refopening","stop","damage"))
    parser.add_argument("phase", type=int, nargs="?", default=1, choices=(1,2))
    args=parser.parse_args()
    if args.test=="prepare":
        prepare(args.mode)
    else:
        run(args.mode,args.phase,args.test)
