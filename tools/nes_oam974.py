"""Measure and accelerate expansion of the checked four-byte OAM seed."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_page963
from check_nes_blank959 import directory, read
from check_nes_output970 import packet_path, replay
from nes_blank959 import ORIGIN, LOADER_SOURCE, build
from nes_page963 import PACKED
from nes_token973 import source
from build_nes_trace_replay import Code

WORK=PACKED.parents[1]/"nes-oam974"
CONTROL=WORK.with_name("nes-oam974-control")
INLINE=WORK.with_name("nes-oam974-inline")
WIDE=WORK.with_name("nes-oam974-wide")
WIDE_CONTROL=WORK.with_name("nes-oam974-wide-control")


def prepare_wide():
    body=bytearray((PACKED/"body.bin").read_bytes())
    labels=read(PACKED/"labels.json")
    end=labels["repeat_done227"]-ORIGIN
    site=body.index(bytes.fromhex("54 7f 7f ab"),end-48,end)
    c=Code(ORIGIN+len(body))
    # A = length-5, X/Y = seed and destination (seed+4).
    # MVN writes its low nibble + 1 bytes; Y then points at the first full group.
    c.emit(0x48,0x29,15,0)
    c.label("oam_prefix974")
    c.emit(0x54,0x7f,0x7f,0x68,0x4a,0x4a,0x4a,0x4a,0xa8)
    c.branch(0xf0,"done974")
    c.label("oam_loop974")
    for half in (0,2):
        c.absolute(0xbd,half)
        for offset in range(half,16,4):
            c.absolute(0x9d,offset+4)
    c.emit(0x8a,0x18,0x69,16,0,0xaa,0x88)
    c.branch(0xd0,"oam_loop974")
    c.label("done974");c.emit(0x60)
    body[site:site+3]=bytes([0x20])+((ORIGIN+len(body))&65535).to_bytes(2,"little")
    body.extend(c.finish());labels.update(c.labels)
    build(LOADER_SOURCE,WIDE,bytes(body),labels,compact_mvn=True,minimum=2,short_pairs=True,shared_byte=True,near_end=True)


def prepare(inline):
    body=bytearray((PACKED/"body.bin").read_bytes())
    labels=read(PACKED/"labels.json")
    old=bytes.fromhex("8b a6 7a a5 7a 18 69 04 00 a8 ad 0c 12 38 e9 05 00 54 7f 7f ab")
    site=body.index(old)
    assert site+len(old)+8==labels["repeat_done227"]-ORIGIN
    # DB is restored before service. D remains zero. Two pairs per pass;
    # for 4 modulo 8 bytes the four original DMA bytes form the prefix.
    # The old unconditional JMP at $2e79 skips the entire 33-byte pad.
    routine=0x7e2e7c if inline else ORIGIN+len(body)
    c=Code(ORIGIN+site)
    c.emit(0x8b,0xad,0x0c,0x12,0x18,0x65,0x7a,0xaa)
    c.emit(0xf4,0x7f,0x7f,0xab,0xab)
    c.emit(0xa0,2,0)
    c.absolute(0x20,routine&65535)
    c.emit(0xab)
    head=c.finish()
    body[site:site+len(old)]=head+bytes([0xea])*(len(old)-len(head))
    c=Code(routine)
    c.label("oam_loop974")
    c.emit(0x8a,0x38,0xe9,8,0,0xaa,0xc5,0x7a)
    c.branch(0x90,"oam_done974")
    c.emit(0xb2,0x7a)
    c.absolute(0x9d,0);c.absolute(0x9d,4)
    c.emit(0xb1,0x7a)
    c.absolute(0x9d,2);c.absolute(0x9d,6)
    c.branch(0x80,"oam_loop974")
    c.label("oam_done974");c.emit(0x60)
    code=c.finish()
    if inline:
        off=routine-ORIGIN
        assert body[off-3:off+33]==bytes.fromhex("4c 9d 2e")+bytes([0xea])*33
        assert len(code)<=33 and not any(routine<=v<routine+33 for v in labels.values())
        body[off:off+len(code)]=code
    else:
        body.extend(code)
    labels.update(c.labels)
    build(LOADER_SOURCE,INLINE if inline else WORK,bytes(body),labels,
          compact_mvn=True,minimum=2,short_pairs=True,shared_byte=not inline)


def trace(temp,phase):
    folder=directory(temp,phase,"973before232","cold")
    out=temp/f"nes-974-trace-p{phase}"
    labels=read(PACKED/"labels.json")
    body=(PACKED/"body.bin").read_bytes()
    end=labels["repeat_done227"]
    mvn=ORIGIN+body.index(bytes.fromhex("54 7f 7f ab"),end-ORIGIN-48,end-ORIGIN)
    checks={"rule":labels["repeat227"],"data":labels["data"],"literal":labels["literal1814"],
            "dma":labels["literal_length227"],"expand":mvn,"expanded":mvn+3,
            "service":labels["service"],"accept":labels["accepted"]}
    hooks="""local seen974={}
local f974=assert(io.open(ROOT..'/oam974.txt','w'))
local function mark974(key)
 if packet and pw(8)==911 and pb(0)==8 and not seen974[key] then
  seen974[key]=true; f974:write(key,' ',emu.getState().masterClock,'\\n');f974:flush()
 end
end
"""
    for name,address in checks.items():
        hooks+=f"checkedMem527(function()mark974('{name}')end,emu.callbackType.exec,{address})\n"
    original=Path.read_text
    def instrument(path,*args,**kwargs):
        s=original(path,*args,**kwargs)
        if path==folder/"capture.lua":
            marker="local function step920(key)"
            assert s.count(marker)==1
            s=s.replace(marker,hooks+marker)
        return s
    packets,_=packet_path(folder,911)
    with patch.object(Path,"read_text",instrument):
        replay(temp,folder,out,"control",packets,911)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("trace","build","run"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--control",action="store_true")
    p.add_argument("--inline",action="store_true")
    p.add_argument("--wide",action="store_true")
    a=p.parse_args()
    if a.action=="trace":
        trace(a.temp,a.phase)
    elif a.action=="run":
        rom=WIDE_CONTROL if a.wide and a.control else WIDE if a.wide else INLINE if a.inline else CONTROL if a.control else WORK
        with patch.object(nes_page963,"PACKED",rom):
            nes_page963.simulate(a.temp,a.phase,"cold",True,source("before232"),True,
                                 tag="974widecontrol" if a.wide and a.control else "974wide" if a.wide else "974inline" if a.inline else "974control" if a.control else "974oam",edition=966)
    elif a.wide and a.control:
        build(LOADER_SOURCE,WIDE_CONTROL,(PACKED/"body.bin").read_bytes(),read(PACKED/"labels.json"),
              compact_mvn=True,minimum=2,short_pairs=True,shared_byte=True,near_end=True)
    elif a.wide:
        prepare_wide()
    elif a.control:
        build(LOADER_SOURCE,CONTROL,(PACKED/"body.bin").read_bytes(),read(PACKED/"labels.json"),
              compact_mvn=True,minimum=2,short_pairs=True,shared_byte=True)
    else:
        prepare(a.inline)
