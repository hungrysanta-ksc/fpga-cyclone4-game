"""Move the compact two-row section check to its last accepted literal.

The incoming SEAL still authorizes the frame, checks every section cursor and
compares all required coverage bits with the bank receipts. Other layouts and
non-adjacent SEALs use the original validator.
"""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_window837 import ORIGIN, OUT as BASE, PROBES, codec, pack
from nes_raw506 import once, sha
from replay_nes_charge836 import trace
from analyze_nes_map830 import window
from replay_nes_section832 import run
from replay_nes_repeat833 import replay
from replay_nes_window837 import MirrorLink, main, reject

OUT = PROBES / "nes-admission838"
CLIENT = OUT / "client"
ARM = PROBES / "nes-output823/link-837palette"
PROOF = 0x1502


def build():
    parent = BASE / "client-sticky"
    body = bytearray((parent / "body.bin").read_bytes())
    labels = json.loads((parent / "labels.json").read_bytes())
    c = Code(ORIGIN + len(body))
    c.labels.update(labels)

    def jsr(name):
        c.absolute(0x20, c.labels[name] & 65535)

    def hook(address, expected, name, opcode):
        offset = address - ORIGIN
        assert body[offset:offset+3] == expected
        body[offset:offset+3] = bytes([opcode]) + (c.labels[name] & 65535).to_bytes(2, "little")

    def test(address, value, other):
        c.absolute(0xad, address)
        c.emit(0xc9)
        c.word(value)
        c.branch(0xd0, other)

    c.label("accept838")
    # Every successful ordinary admission expires the previous proof. BEGIN
    # also passes here. Only the completed literal section can issue a new one.
    c.absolute(0x9c, PROOF)
    test(0x1200, 0x0502, "exit838")
    test(0x108a, 1754, "exit838")
    # The current bank now holds 1121+384+249 bytes. Test the candidate
    # meaning against WRAM, and restore the preceding display's metadata.
    # Do not call compact489 early: it can invalidate a bank history.
    for address, value in ((0x100a,3418),(0x1240,2),(0x123a,0x1e),(0x125e,0x6ae1)):
        c.absolute(0xad, address)
        c.emit(0x48, 0xa9)
        c.word(value)
        c.absolute(0x8d, address)
    jsr("validate181")
    for address in (0x125e,0x123a,0x1240,0x100a):
        c.emit(0x68)
        c.absolute(0x8d, address)
    c.branch(0x90, "exit838")
    c.label("record838")
    c.absolute(0xee, PROOF)
    c.label("exit838")
    c.absolute(0xad, 0x1200)
    c.jump("acceptedResume838")
    c.labels["acceptedResume838"] = labels["accepted"]+3
    hook(labels["accepted"], bytes.fromhex("ad0012"), "accept838", 0x4c)

    c.label("invalidate838")
    c.absolute(0x9c, PROOF)
    c.absolute(0x9c, 0x14d0)
    c.jump("invalidateResume838")
    c.labels["invalidateResume838"] = labels["invalidate635"]+3
    hook(labels["invalidate635"], bytes.fromhex("9cd014"), "invalidate838", 0x4c)

    c.label("seal838")
    c.absolute(0xad, PROOF)
    c.branch(0xf0, "full838")
    # Common SEAL has already checked serial/generation, target bank, order
    # and exact section extents. Bind the two speculative semantic fields.
    test(0x108a,1754,"full838")
    test(0x1240,2,"full838")
    test(0x123a,0x1e,"full838")
    c.label("reuse838")
    c.emit(0x38,0x60)
    c.label("full838")
    c.jump("validate181")
    old = bytes([0x20])+(labels["validate181"] & 65535).to_bytes(2,"little")
    pos = body.index(old, labels["seal"]-ORIGIN, labels["retire181"]-ORIGIN)
    hook(ORIGIN+pos, old, "seal838", 0x20)
    body.extend(c.finish())
    used = 260 + len(pack(bytes(body),0))
    # Keep the target limit as a separate gate. If exceeded, use precisely
    # the occupied bytes for a bootable emulator-only diagnostic.
    with patch.object(codec,"pack",pack), patch.object(codec,"STORED",max(codec.STORED,used)):
        codec.build(PROBES/"nes-reuse635/client04",CLIENT,edit_body=lambda *_:bytes(body),
                    allow_extension=True,body_limit=0x2000,prefix_sizes=[0],medium_pages=True,
                    short_errors=True,boot_bytes=260,fast_backrefs=True)
    (CLIENT/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")
    info=json.loads((CLIENT/"build.json").read_bytes())
    info.update(physical_ROM_B=used+64,program_bytes=used+64,physical_free_B=5056-used,
                board_limit_B=5120,proof_WRAM_B=2,semantic_stack_extra_B=8)
    (CLIENT/"build.json").write_text(json.dumps(info,indent=2)+"\n")


def observe(s):
    labels=json.loads((CLIENT/"labels.json").read_bytes())
    hook="local log838=assert(io.open(ROOT..'/admission838.txt','w'))\n"
    for name in ("record838","reuse838","full838","coverage212"):
        hook+=f"""checkedMem527(function()
 if packet then log838:write(string.format('%d {name} %d %d\\n',pw(8),pb(0),emu.getState().masterClock));log838:flush() end
end,emu.callbackType.exec,{labels[name]})
"""
    return once(trace(CLIENT,False)(s),"checkedMem527(function()rpc()end",hook+"checkedMem527(function()rpc()end")


def isolated(s):
    # Preserve the 837 boot, every prior display and their beam/IRQ phases.
    old=(BASE/"client-sticky/body.bin").read_bytes()
    new=(CLIENT/"body.bin").read_bytes()
    edits=[f"emu.write({0x2000+i},{v},emu.memType.snesWorkRam)"
           for i,v in enumerate(new) if i>=len(old) or old[i]!=v]
    at="  lastStatus=ack[1];"
    return observe(once(s,at,"  if pw(8)==909 and pb(0)==3 and ack[1]==1 then\n"+
                        "\n".join(edits)+"\n  end\n"+at))


def guard(a):
    def inject(s):
        # Packet bytes are changed at dequeue, after ARM serialization.
        actions={"metadata":"if pb(0)==3 then b[35]=0x18 end",
                 "identity":"if pb(0)==3 then b[9]=b[9]~1 end",
                 "table":"if pb(0)==2 and pb(1)==5 and pw(10)==1505 then b[18]=0x7f end"}
        s=once(s,"local MODE='normal'",f"local MODE='838{a.mode}'")
        s=once(s,"local FAULT=905","local FAULT=910")
        return observe(once(s,"  if MODE=='bad_mode'","  "+actions[a.mode]+"\n  if MODE=='bad_mode'"))
    tag="838admit"+a.mode
    try:
        run(a.arm,a.phase,a.temp,a.budget,arm=ARM,client=CLIENT,tag=tag,adapt=inject)
    except (AssertionError,BrokenPipeError):
        folder=a.temp/f"nes-tile821-demoB-jointmirror-p{a.phase}-{tag}"
        rows=window(folder)
        assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910))
        errors=[r for r in rows if r["event"]=="ack" and r["value"]>=224]
        assert len(errors)==1 and errors[0]["op"]==3 and errors[0]["value"]==224
        entries=(folder/"admission838.txt").read_text().splitlines()
        assert not any(r.startswith("910 reuse838") for r in entries)
        assert any(r.startswith("910 record838") for r in entries)==(a.mode!="table")
    else:
        raise AssertionError("bad section or identity accepted")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("build","demo","opening","pulse","coverage","damage","fixed","metadata","table","identity"))
    p.add_argument("phase",type=int,nargs="?",default=1)
    a=p.parse_args()
    a.temp=Path.home()/"AppData/Local/Temp"
    a.budget=Path.home()/"Downloads/nes-budget-mmc826.txt"
    a.arm="palette"
    tag="838admit"
    if a.mode=="build":
        build()
    elif a.mode=="fixed":
        run(a.arm,a.phase,a.temp,a.budget,arm=ARM,client=BASE/"client-sticky",tag=tag+"fixed",adapt=isolated)
    elif a.mode in ("metadata","identity","table"):
        guard(a)
    elif a.mode=="opening":
        with patch.object(sys,"argv",["replay","","","","","",tag,str(a.budget)]):
            main(PROBES/"nes-tile821/extra01","earlyB","jointmirror",a.phase,a.temp,
                 arm=ARM/"src",link_class=MirrorLink,client=CLIENT,client_hash=sha(CLIENT/"sink165.sfc"))
    elif a.mode in ("coverage","pulse"):
        a.fault=a.mode
        reject(a,CLIENT,ARM,tag+a.mode)
    else:
        fault=a.mode if a.mode=="damage" else None
        replay(a.arm,a.phase,a.temp,a.budget,tag=tag+(fault or ""),client=CLIENT,arm=ARM,fault=fault,extra_trace=observe)
