"""Validate a complete scroll literal while later sections are still on SPI."""
import argparse
from pathlib import Path
from unittest.mock import patch

import boot_nes_column854 as boot
import nes_page963
import nes_proof989 as common
from build_nes_trace_replay import Code
from check_nes_plan975 import read
from nes_blank959 import ORIGIN, LOADER_SOURCE
from nes_blank960 import PACKED
from nes_tile985 import work

ROM=common.ROM.parent/"scroll"
FLAG=common.PROOF
SHADOW=common.COPY


def build():
    labels=read(PACKED/"labels.json")
    body=bytearray((PACKED/"body.bin").read_bytes())
    c=Code(ORIGIN+len(body))
    c.labels.update(labels)
    def imm(op,value):
        c.emit(op)
        c.word(value)
    def need(op,label):
        c.emit(op,3)
        c.jump(label)
    def hook(pc,old,label):
        i=pc-ORIGIN
        assert body[i:i+3]==old
        body[i:i+3]=bytes([0x4c])+(c.labels[label]&65535).to_bytes(2,"little")
    def resume(pc):
        c.absolute(0x4c,pc&65535)

    # Sections 3 and 4 cannot write the section 5 WRAM range. Known tile
    # commands target VRAM staging. For section 5 only disjoint appends pass.
    c.label("header989")
    c.absolute(0xad,FLAG)
    c.branch(0xf0,"resume989")
    c.absolute(0xad,0x1200)
    for word in (3,0x0007,0x0107,0x0302,0x0304,0x0402,0x0404,0x0408):
        imm(0xc9,word)
        c.branch(0xf0,"resume989")
    imm(0xc9,0x0502)
    c.branch(0xf0,"offset989")
    imm(0xc9,0x0505)
    c.branch(0xd0,"expire989")
    c.label("offset989")
    c.absolute(0xad,0x120a)
    imm(0xc9,21)
    c.branch(0xb0,"resume989")
    c.label("expire989")
    c.absolute(0x9c,FLAG)
    c.label("resume989")
    c.absolute(0xad,0x1200)
    resume(labels["header"]+12)
    hook(labels["header"]+9,bytes.fromhex("ad0012"),"header989")

    c.label("invalidate989")
    c.absolute(0x9c,FLAG)
    c.absolute(0x9c,0x14d0)
    resume(labels["invalidate635"]+3)
    hook(labels["invalidate635"],bytes.fromhex("9cd014"),"invalidate989")

    c.label("accepted989")
    for addr,val in ((0x1200,0x0502),(0x120a,0),(0x108a,21)):
        c.absolute(0xad,addr)
        imm(0xc9,val)
        need(0xf0,"ordinary989")
    c.label("early989")
    c.absolute(0xae,0x1020)
    c.emit(0xe2,0x20)
    # Each of the four counts must be in 1..127, followed by a zero
    # terminator. Sum in 16 bits so 224+256 cannot pass.
    c.long(0xbf,0x7f6514)
    need(0xf0,"fallback989")
    c.emit(0xc2,0x20)
    c.absolute(0x9c,0x74)
    for at in (0,5,10,15):
        c.long(0xbf,0x7f6500+at)
        imm(0x29,255)
        need(0xd0,"ordinary989")
        imm(0xc9,128)
        need(0x90,"ordinary989")
        c.emit(0x18,0x65,0x74,0x85,0x74)
    imm(0xc9,224)
    need(0xf0,"ordinary989")
    for off in (*range(0,20,2),19):
        c.long(0xbf,0x7f6500+off)
        c.absolute(0x8d,SHADOW+off)
    c.label("record989")
    imm(0xa9,1)
    c.absolute(0x8d,FLAG)
    c.label("ordinary989")
    c.absolute(0xad,0x1200)
    resume(labels["accepted"]+3)
    c.label("fallback989")
    c.emit(0xc2,0x20)
    c.jump("ordinary989")
    hook(labels["accepted"],bytes.fromhex("ad0012"),"accepted989")

    c.label("seal989")
    c.absolute(0xad,FLAG)
    need(0xd0,"full989")
    c.absolute(0x9c,FLAG)
    c.absolute(0xae,0x1020)
    for off in (*range(0,20,2),19):
        c.long(0xbf,0x7f6500+off)
        c.absolute(0xcd,SHADOW+off)
        need(0xf0,"damage989")
    c.label("reuse989")
    c.emit(0xe2,0x20)
    c.store(0x72,0x7f)
    c.emit(0xc2,0x20)
    imm(0xa0,20)
    i=labels["scroll_end181"]-ORIGIN
    assert body[i:i+10]==bytes.fromhex("a574c9e000f0034c5631")
    resume(labels["scroll_end181"]+10)
    c.label("damage989")
    c.emit(0x18,0x60)
    c.label("full989")
    c.jump("validate181")
    old=b'\x20'+(labels["validate181"]&65535).to_bytes(2,"little")
    i=body.index(old,labels["seal"]-ORIGIN,labels["retire181"]-ORIGIN)
    body[i+1:i+3]=(c.labels["seal989"]&65535).to_bytes(2,"little")
    body.extend(c.finish())
    with patch.object(boot,"STORED",6000):
        boot.build(LOADER_SOURCE,ROM,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


if __name__=="__main__":
    import subprocess
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("build","run"));p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,default=1);p.add_argument("--aligned",action="store_true")
    p.add_argument("--between",action="store_true")
    a=p.parse_args()
    if a.action=="build":build()
    else:
        with patch.object(common,"ROM",ROM),patch.object(nes_page963,"PACKED",PACKED if a.aligned else ROM),patch.object(subprocess,"Popen",common.launch(subprocess.Popen,a.aligned)):
            nes_page963.simulate(a.temp,a.phase,"cold",True,work("between" if a.between else "after"),True,
                                 tag="989scroll"+("prefix" if a.aligned else "")+("between" if a.between else ""),edition=966)
