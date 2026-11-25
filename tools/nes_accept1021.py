"""Move one-row HDMA semantics and compact DMA source preparation to acceptance."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import boot_nes_column854 as boot
import replay_nes_tail1013 as joint
from build_nes_trace_replay import Code
from nes_blank959 import LOADER_SOURCE
from nes_blank960 import PACKED
from nes_tail1013 import ROOT, once
from nes_raw506 import sha

OUT = ROOT.parent / "probes/nes-accept1021/client"
ORIGIN = 0x7e2000
PROOF = 0x15f0
SHADOW = 0x1600
TABLE = 0x6961 + 192
SIZE = 1121 + 192 + 249


def build():
    ref = json.loads((ROOT/"analysis/trial1012-package.json").read_bytes())
    assert sha(PACKED/"sink165.sfc") == ref["client"]
    body = bytearray((PACKED/"body.bin").read_bytes())
    labels = json.loads((PACKED/"labels.json").read_bytes())
    c = Code(ORIGIN + len(body))
    c.labels.update(labels)

    def hook(addr, before, name, op=0x4c):
        i = addr - ORIGIN
        assert body[i:i+3] == before
        body[i:i+3] = bytes([op]) + (c.labels[name]&65535).to_bytes(2,"little")

    def jsr(name):
        c.absolute(0x20,c.labels[name]&65535)

    def test(addr, value, fail):
        c.absolute(0xad,addr)
        c.emit(0xc9); c.word(value)
        c.branch(0xd0,fail)

    # Both banks use one tentative proof. A BEGIN, fault or STOP expires it.
    for name, old in (("begin",0x14d8),("invalidate635",0x14d0)):
        c.label(name+"1021")
        c.absolute(0x9c,PROOF)
        c.absolute(0x9c,old)
        c.labels[name+"Resume"]=labels[name]+3
        c.jump(name+"Resume")
        hook(labels[name], bytes([0x9c,old&255,old>>8]),name+"1021")

    # Verify exact active bytes again at SEAL. Copy 22 bytes per table
    # (one harmless padding byte) and bind all three 16-bit lengths to 21.
    def snapshot(compare):
        loop = "compare1021" if compare else "copy1021"
        c.absolute(0xae,0x1020); c.emit(0xa0,0,0)
        for off in (243,245,247):
            c.long(0xbf,0x7f0000+TABLE+off); c.emit(0xc9,21,0); c.branch(0xd0,"miss1021")
        c.long(0xbf,0x7f6514); c.emit(0x29,255,0); c.branch(0xd0,"miss1021")
        c.label(loop)
        for i,addr in enumerate((0x6500,TABLE,TABLE+81,TABLE+162)):
            c.long(0xbf,0x7f0000+addr)
            c.absolute(0xd9 if compare else 0x99, SHADOW+i*22)
            if compare:
                c.branch(0xd0,"miss1021")
        c.emit(0xe8,0xe8,0xc8,0xc8,0xc0,22,0); c.branch(0xd0,loop)

    c.label("accept1021")
    c.absolute(0xad,0x1201); c.emit(0x29,255,0,0xc9,5,0); c.branch(0xd0,"resume1021")
    c.absolute(0x9c,PROOF)
    test(0x1200,0x0502,"resume1021")
    test(0x108a,SIZE,"resume1021")
    c.absolute(0xad,0x120a); c.emit(0xc9); c.word(SIZE-240); c.branch(0xd0,"resume1021")
    c.jump("precheck1021")
    c.label("resume1021"); c.absolute(0xad,0x1200)
    c.labels["acceptedResume"]=labels["accepted"]+3
    c.jump("acceptedResume")
    hook(labels["accepted"],bytes.fromhex("ad0012"),"accept1021")

    c.label("precheck1021")
    # Validate against committed WRAM writes, without altering the current
    # display metadata or the bank's prior raw-pattern history.
    for addr,value in ((0x100a,3418),(0x1240,1),(0x123a,0x1e),(0x125e,TABLE)):
        c.absolute(0xad,addr); c.emit(0x48,0xa9); c.word(value); c.absolute(0x8d,addr)
    jsr("validate181")
    for addr in (0x125e,0x123a,0x1240,0x100a):
        c.emit(0x68); c.absolute(0x8d,addr)
    c.branch(0x90,"resume1021")
    # 'miss' returns carry clear to the caller in either use of snapshot.
    c.emit(0x20,0,0); c.jumps.append((len(c.data)-2,"take1021"))
    c.branch(0x90,"resume1021")
    c.emit(0xa9); c.word(TABLE); c.absolute(0x8d,PROOF); c.jump("resume1021")
    c.label("take1021"); snapshot(False); c.emit(0x38,0x60)
    c.label("miss1021"); c.emit(0x18,0x60)
    c.label("verify1021"); snapshot(True); c.emit(0x38,0x60)

    c.label("layout1021")
    # The common caller already compared the section cursors and generation.
    # The prepared pointer is consumed only for its exact bound layout.
    test(PROOF,TABLE,"slow1021"); test(0x100a,SIZE,"slow1021")
    test(0x1240,1,"slow1021"); test(0x123a,0x1e,"slow1021")
    c.absolute(0xad,PROOF); c.absolute(0x8d,0x125e)
    c.emit(0xa9,192,0); c.absolute(0x8d,0x1258); c.absolute(0x9c,0x125c)
    start = labels["compact_rows489"]-ORIGIN
    cut = body.index(bytes.fromhex("ae3410e220bd5a12"),start)
    c.labels["bank1021"]=ORIGIN+cut; c.jump("bank1021")
    c.label("slow1021"); c.absolute(0x9c,PROOF); c.jump("compact489")
    c.label("semantics1021"); c.absolute(0xad,PROOF); c.branch(0xd0,"fast1021"); c.jump("validate181")
    c.label("fast1021"); c.jump("verify1021")
    for name,new in (("compact489","layout1021"),("validate181","semantics1021")):
        old=bytes([0x20])+(labels[name]&65535).to_bytes(2,"little")
        addr=body.index(old,labels["seal"]-ORIGIN,labels["retire181"]-ORIGIN)
        hook(ORIGIN+addr,old,new,0x20)
    body.extend(c.finish())
    # Emit an emulator diagnostic even if it exceeds the installed ROM.
    with patch.object(boot,"STORED",8192):
        boot.build(LOADER_SOURCE,OUT,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


def observe(lua, labels, fault=None):
    keys = ("seal_sizes","compact489","local165_entry","map_coverage212","prepare665","precheck1021",
            "copy1021","layout1021","slow1021","fast1021","verify1021","semantics1021","bank1021")
    hooks = []
    for key in keys:
        if key in labels:
            hooks.append(f"checkedMem527(function()if packet and pw(8)==908 then sample516('{key}') end end,emu.callbackType.exec,{labels[key]})")
    if fault:
        hooks.append(f"""checkedMem527(function()
 if packet and pw(8)==908 and pb(0)==3 then
  assert(word({PROOF})=={TABLE})
  local addr=0x10000+word(0x1020)+{TABLE}+1
  emu.write(addr,rd(addr)~1,emu.memType.snesWorkRam)
 end end,emu.callbackType.exec,{labels['seal']})""")
    return once(lua,"checkedMem527(function()rpc()end","\n".join(hooks)+"\ncheckedMem527(function()rpc()end")


def run(temp, phase):
    real_main = joint.main
    def main(*args, **kwargs):
        kwargs.update(client=OUT,client_hash=sha(OUT/"sink165.sfc"))
        return real_main(*args, **kwargs)
    labels=json.loads((OUT/"labels.json").read_bytes())
    with patch.object(joint,"main",main):
        joint.run(temp,phase,"control",tag="1021-accept",observe_client=lambda lua: observe(lua,labels))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("build","joint")); p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,nargs="?",choices=(1,2))
    args=p.parse_args()
    if args.action=="build": build()
    else: run(args.temp,args.phase)
