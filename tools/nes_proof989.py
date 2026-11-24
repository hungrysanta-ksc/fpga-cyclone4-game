"""Check a completed one-row HDMA section before tile DMA and bind it at SEAL."""
import argparse
import subprocess
from pathlib import Path
from unittest.mock import patch

import boot_nes_column854 as boot
import nes_page963
from build_nes_trace_replay import Code
from check_nes_plan975 import directory, packet_path, read, replay
from nes_blank959 import LOADER_SOURCE, ORIGIN
from nes_blank960 import PACKED
from nes_native_local165 import call
from nes_raw506 import once
from nes_tile985 import work

ROM = work("after").parent / "nes-proof989" / "rom02"
PROOF = 0x1800
COPY = PROOF + 2
TABLE = 0x6961 + 192


def build():
    labels = read(PACKED / "labels.json")
    body = bytearray((PACKED / "body.bin").read_bytes())
    c = Code(ORIGIN + len(body))
    c.labels.update(labels)

    def imm(op, n):
        c.emit(op)
        c.word(n)

    def hook(pc, old, label, op=0x4c):
        i = pc - ORIGIN
        assert len(old) == 3 and body[i:i+3] == old
        body[i:i+3] = bytes([op]) + (c.labels[label] & 65535).to_bytes(2, "little")

    def require(op, target):
        c.emit(op, 3)
        c.jump(target)

    def eq_at(addr, value, failure):
        c.absolute(0xad, addr)
        imm(0xc9, value)
        require(0xf0, failure)

    def resume(addr):
        c.absolute(0x4c, addr & 65535)

    # Header DMA has completed. Every non-SEAL expires the proof before its
    # payload can alter either bank, including a same-value partial rewrite.
    c.label("header989")
    c.absolute(0xad, 0x1200)
    imm(0xc9, 3)
    c.branch(0xf0, "keep989")
    c.absolute(0x9c, PROOF)
    c.label("keep989")
    resume(labels["header"] + 12)
    hook(labels["header"] + 9, bytes.fromhex("ad0012"), "header989")

    c.label("invalidate989")
    c.absolute(0x9c, PROOF)
    c.absolute(0x9c, 0x14d0)
    resume(labels["invalidate635"] + 3)
    hook(labels["invalidate635"], bytes.fromhex("9cd014"), "invalidate989")

    def shadow(check):
        # These four active HDMA streams are 21 bytes long. Include the
        # following padding byte so all reads can use native 16-bit words.
        suffix = "check" if check else "copy"
        c.absolute(0xae, 0x1020)
        imm(0xa0, 0)
        c.label(suffix + "989")
        for n, addr in enumerate((0x6500, TABLE, TABLE+81, TABLE+162)):
            c.long(0xbf, 0x7f0000 + addr)
            c.absolute(0xd9 if check else 0x99, COPY + n*22)
            if check:
                require(0xf0, "damage989")
        c.emit(0xe8, 0xe8, 0xc8, 0xc8)
        imm(0xc0, 22)
        c.branch(0xd0, suffix + "989")
        c.absolute(0xae, 0x1020)
        for n in (0, 2, 4):
            c.long(0xbf, 0x7f0000 + TABLE + 243 + n)
            c.absolute(0xcd if check else 0x8d, COPY+88+n)
            if check:
                require(0xf0, "damage989")

    c.label("accepted989")
    eq_at(0x1200, 0x0502, "ordinary989")
    eq_at(0x120a, 1322, "ordinary989")
    eq_at(0x108a, 1562, "ordinary989")
    c.absolute(0xae, 0x1020)
    c.long(0xbf, 0x7f0000 + TABLE + 243)
    imm(0xc9, 21)
    require(0xf0, "ordinary989")
    c.long(0xbf, 0x7f6514)
    imm(0x29, 255)
    require(0xf0, "ordinary989")
    fields = ((0x100a,3418),(0x1240,1),(0x123a,0x1e),(0x125e,TABLE))
    for a,v in fields:
        c.absolute(0xad,a)
        c.emit(0x48)
        imm(0xa9,v)
        c.absolute(0x8d,a)
    c.label("early989")
    call(c, "validate181")
    for a,_ in reversed(fields):
        c.emit(0x68)
        c.absolute(0x8d,a)
    require(0xb0, "ordinary989")
    shadow(False)
    c.label("record989")
    imm(0xa9,1)
    c.absolute(0x8d, PROOF)
    c.label("ordinary989")
    c.absolute(0xad, 0x1200)
    resume(labels["accepted"] + 3)
    hook(labels["accepted"], bytes.fromhex("ad0012"), "accepted989")

    c.label("seal989")
    c.absolute(0xad, PROOF)
    require(0xd0, "full989")
    c.absolute(0x9c, PROOF)
    for a,v in fields:
        eq_at(a,v,"full989")
    shadow(True)
    c.label("reuse989")
    c.emit(0x38,0x60)
    c.label("damage989")
    c.emit(0x18,0x60)
    c.label("full989")
    c.jump("validate181")
    old = bytes([0x20])+(labels["validate181"] & 65535).to_bytes(2, "little")
    pos = body.index(old, labels["seal"]-ORIGIN, labels["retire181"]-ORIGIN)
    hook(ORIGIN+pos,old,"seal989",0x20)
    body.extend(c.finish())
    with patch.object(boot,"STORED",6000):
        boot.build(LOADER_SOURCE,ROM,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


def observer(source):
    labels=read(ROM/"labels.json")
    code="local log989=assert(io.open(ROOT..'/proof989.csv','w'))\n"
    for key in ("early989","record989","reuse989","damage989","invalidate989","full989","seal989"):
        code+=f"""checkedMem527(function()
 if packet and pw(8)==911 then
  log989:write('{key},'..emu.getState().masterClock..','..word({PROOF})..'\\n');log989:flush()
 end
end,emu.callbackType.exec,{labels[key]})
"""
    return once(source,"local function loaded()",code+"local function loaded()")


def align_boot(source):
    old=(PACKED/"body.bin").read_bytes()
    candidate=(ROM/"body.bin").read_bytes()
    writes=[f"emu.write({0x2000+i},{b},emu.memType.snesWorkRam)"
            for i,b in enumerate(candidate) if i>=len(old) or old[i]!=b]
    anchor="packet=requests[index];sample516"
    return once(source,anchor,"packet=requests[index]\n if pw(8)==911 and pb(0)==1 then\n"+
                "\n".join(writes)+"\n end\n sample516")


def launch(original, aligned):
    def invoke(args,*a,**k):
        if "--testRunner" in args:
            f=Path(args[args.index("--testRunner")+1])
            script=f.read_text(encoding="utf-8")
            f.write_text(observer(align_boot(script) if aligned else script),encoding="utf-8",newline="\n")
        return original(args,*a,**k)
    return invoke


def run(temp,phase,where,aligned):
    with patch.object(nes_page963,"PACKED",PACKED if aligned else ROM),patch.object(subprocess,"Popen",launch(subprocess.Popen,aligned)):
        nes_page963.simulate(temp,phase,"cold",True,work(where),True,tag=("989prefix" if aligned else "989v2")+where,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("build","run"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--where",choices=("between","after"),default="after")
    p.add_argument("--align-prefix",action="store_true")
    a=p.parse_args()
    if a.action=="build":build()
    else:run(a.temp,a.phase,a.where,a.align_prefix)
