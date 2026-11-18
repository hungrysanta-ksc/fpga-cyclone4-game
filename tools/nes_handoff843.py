"""Test a single checked BG submission on either side of the 768-byte map DMA."""
import argparse
import json
import sys
from unittest.mock import patch

import nes_tile842 as prior
from nes_pair839 import once

OUT = prior.section.PROBES / "nes-handoff843"
BASE = prior.arm("defer1")
CLIENT = OUT / "client"


def receiver():
    from nes_pair839 import Code, ORIGIN, codec, pack
    labels=json.loads((prior.CLIENT/"labels.json").read_bytes())
    body=bytearray((prior.CLIENT/"body.bin").read_bytes())
    c=Code(ORIGIN+len(body))
    c.labels.update(labels)
    # handoff839 already checked STOP, the next queue head and the live tail.
    at=body.index(bytes.fromhex("290070c90040d0"),labels["handoff839"]-ORIGIN)
    c.label("source843")
    c.emit(0x89,0xff,0x7f)  # BIT #$7fff, BG slot zero in either WRAM bank
    c.branch(0xd0,"other843")
    c.long(0xbf,0x7e4004)
    c.emit(0xc9,16,0)
    c.branch(0xd0,"skip843")
    c.absolute(0x4c,(ORIGIN+at+17)&65535)  # TAY, SEP then original beam latch
    assert body[at+17:at+20]==bytes.fromhex("a8e220")
    c.label("other843");c.emit(0x29,0,0x70,0xc9,0,0x40)
    c.branch(0xd0,"skip843")
    c.absolute(0x4c,(ORIGIN+at+8)&65535)
    c.label("skip843");c.jump("finish839")
    body[at:at+8]=bytes([0x4c])+(c.labels["source843"]&65535).to_bytes(2,"little")+bytes(5)
    at=labels["pair839"]-ORIGIN-4
    assert body[at:at+4]==bytes.fromhex("c9eeb003")
    # Accepted OBJ offsets and lengths are 32-byte aligned (bulk194).
    c.label("beam843")
    c.emit(0xc0,16,0);c.branch(0xd0,"obj843")
    c.emit(0xc9,255);c.branch(0xb0,"defer843")
    c.label("bg843");c.jump("map_beam_ok526")  # includes fresh STOP/head checks before MDMAEN
    c.label("obj843");c.emit(0xc9,238);c.branch(0xb0,"defer843");c.jump("pair839")
    c.label("defer843");c.jump("defer839")
    body[at:at+4]=bytes([0x4c])+(c.labels["beam843"]&65535).to_bytes(2,"little")+bytes(1)
    body.extend(c.finish())
    used=260+len(pack(bytes(body),0))
    with patch.object(codec,"pack",pack),patch.object(codec,"STORED",max(5056,used)):
        codec.build(prior.section.PROBES/"nes-reuse635/client04",CLIENT,edit_body=lambda *_:bytes(body),
                    allow_extension=True,body_limit=8192,prefix_sizes=[0],medium_pages=True,
                    short_errors=True,boot_bytes=260,fast_backrefs=True)
    (CLIENT/"labels.json").write_text(json.dumps(c.labels,indent=2))
    (CLIENT/"cost.json").write_text(json.dumps({"program_bytes":used+64,"capacity":5120}))


def bg_oracle(lua):
    label=json.loads((CLIENT/"labels.json").read_bytes())
    lua=once(lua,"local selected839=false",f"""local selectedBG843=false
checkedMem527(function()selectedBG843=true end,emu.callbackType.exec,{label['bg843']})
checkedMem527(function()selectedBG843=false end,emu.callbackType.exec,{label['prefix523']})
local selected839=false""")
    return once(lua,"  if selected839 then","""  if selectedBG843 then
   local st=emu.getState();i=st['cpu.x']
   assert(i==tail and n==16 and src==word(0x1020) and (dst==0 or dst==0xc000))
   assert(beam685.frame==st.frameCount and beam685.line>=225 and beam685.line<=254)
   assert(st.masterClock-beam685.clock<3*1364 and st['ppu.scanline']<=257)
   selectedBG843=false
  elseif selected839 then""")


def arm(mode):
    return BASE.parent / ("link-843" + mode)


def prepare(mode):
    dest = OUT / ("patch-" + mode)
    dest.mkdir(exist_ok=True, parents=True)
    src = BASE / "src"
    name = "nes_native_sink165.c"
    code = (src / name).read_text()
    code = once(code, " bool room;\n if(!nes_plan527_map_credit(s->plan,&room))return false;\n p->section841=true;",
                " p->section841=true;")
    anchor = "   for(unsigned n=0;n<120;n++){"
    offer = """if(p->section841 && s->plan->sent){
    bool room;
    if(!nes_window184_drain(s->plan->window,ack) ||
       !nes_plan527_map_credit(s->plan,&room) ||
       !nes_plan843_return(s->plan))return fail(s,5);
   }"""
    if mode == "before":
        code = once(code, anchor, "   " + offer + "\n" + anchor)
    elif mode == "after":
        end = "    if(s->plan->window->status_flags&8)break;\n   }"
        code = once(code, end, end + "\n   " + offer)
    else:
        raise ValueError(mode)
    (dest / name).write_text(code, newline="\n")
    for name, anchor, addition in (
            ("nes_plan_service200.h", "bool nes_plan527_map_credit", "bool nes_plan843_return(struct nes_plan200 *p);\n"),
            ("nes_plan_service200.c", "static uint32_t token485",
             "bool nes_plan843_return(struct nes_plan200 *p){return complete485(p);}\n")):
        (dest / name).write_text(once((src / name).read_text(), anchor, addition + anchor), newline="\n")


def run(mode, phase, test):
    if test == "opening":
        tag = f"843{mode}opening"
        client = prior.section.REFERENCE
        with patch.object(sys, "argv", ["replay","","","","","",tag,str(prior.BUDGET)]):
            prior.section.main(prior.section.PROBES/"nes-tile821/extra01", "earlyB", "jointmirror",
                               phase, prior.TEMP, arm=arm(mode)/"src", link_class=prior.section.MirrorLink,
                               client=client, client_hash=prior.section.sha(client/"sink165.sfc"))
        return
    runner = prior.replay.run
    tail=test=="tail"
    def tagged(*args, **kwargs):
        kwargs["tag"] = "843" + mode + test
        if tail:
            adapt=kwargs["adapt"]
            kwargs["adapt"]=lambda s:bg_oracle(adapt(s))
        return runner(*args, **kwargs)
    with patch.object(prior.replay, "run", tagged), patch.object(prior, "arm", arm), patch.object(prior,"CLIENT",CLIENT if tail else prior.CLIENT):
        prior.run(mode, phase, "fixed" if tail else test)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("before","after"))
    p.add_argument("test", choices=("prepare","fixed","static","tail","receiver","opening"))
    p.add_argument("phase", type=int, choices=(1,2), nargs="?", default=1)
    a = p.parse_args()
    if a.test == "prepare":
        prepare(a.mode)
    elif a.test=="receiver":
        receiver()
    else:
        run(a.mode,a.phase,a.test)
