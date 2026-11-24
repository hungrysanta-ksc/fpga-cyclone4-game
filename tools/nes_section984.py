"""Exercise a self-contained raw/HDMA tail on the linked ARM and 65816."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import boot_nes_column854 as boot
import nes_page963
from build_nes_trace_replay import Code
from nes_blank960 import LOADER_SOURCE, PACKED
from nes_head980 import baseline
from nes_raw506 import once

WORK = baseline("returned").with_name("nes-section984")


def sender():
    dst = WORK / "link"
    shutil.copytree(baseline("returned") / "link", dst)
    path = dst / "src/nes_native_sink165.c"
    text = path.read_text()
    helper = """static bool compact_tail984(uint8_t *out, const uint8_t *raw,
                            const uint8_t *tables, const uint16_t *sizes) {
 for(unsigned i=0;i<3;i++) {
  const uint8_t *plane=raw+64*i, *table=tables+81*i;
  if(sizes[i]!=21 || memcmp(plane,plane+2,62) ||
     table[21] || memcmp(table+21,table+22,59))return false;
  put16(out+2*i,sizes[i]);
  memcpy(out+6+2*i,plane,2);
  memcpy(out+12+21*i,table,21);
 }
 return true;
}
"""
    text = once(text, "bool nes_sink212_seal(", helper+"bool nes_sink212_seal(")
    start = text.index("  memcpy(joined,raw+prefix,192);")
    end = text.index("  offset+=192;", start)
    old = text[start:end]
    text = once(text, old, """  if(offset==1121 && compact_tail984(joined,raw+prefix,tables,p->patch.size)){
   if(!packet(s,9,5,offset,joined,75))return false;
  }else{
""" + "".join(" "+line for line in old.splitlines(True)) + "  }\n")
    path.write_text(text, newline="\n")


def receiver():
    body = bytearray((PACKED/"body.bin").read_bytes())
    c = Code(0x7e2000+len(body))
    c.labels.update(json.loads((PACKED/"labels.json").read_bytes()))

    def hook(pc, target, name):
        i = pc-0x2000
        assert body[i:i+3] == bytes([0x4c])+(c.labels[target]&65535).to_bytes(2,"little")
        c.label(name)
        body[i+1:i+3] = (c.labels[name]&65535).to_bytes(2,"little")

    def imm(op, n):
        c.emit(op)
        c.word(n)

    def service():
        c.absolute(0x20,c.labels["service"]&65535)
        c.emit(0xf0,3)
        c.jump("stop_packet")

    hook(0x3768,"reuse635","header984")
    imm(0xc9,0x509)
    c.emit(0xf0,3)
    c.jump("reuse635")
    for address,value in ((0x120a,1121),(0x120c,75),(0x120e,0)):
        c.absolute(0xad,address)
        imm(0xc9,value)
        c.branch(0xd0,"reject984")
    for i in range(3):
        c.long(0xaf,0x400010+2*i)
        imm(0xc9,21)
        c.branch(0xd0,"reject984")
    imm(0xa9,441)
    c.absolute(0x8d,0x120c)
    c.jump("data")
    c.label("reject984")
    c.jump("bad_packet")

    hook(0x37ec,"literal1814","value984")
    c.emit(0xc9,9,0xf0,3)
    c.jump("literal1814")
    # X was the section-table index when the common bounds check began.
    imm(0xe0,10)
    c.emit(0xf0,3)
    c.jump("bad_packet")
    c.emit(0xc2,0x20,0xa5,0x7a,0x85,0x60)  # destination offset
    c.emit(0xe2,0x20,0xa9,0x7f,0x85,0x62)
    # Each span is written, then reread against the source. No prior bank
    # contents are assumed. Poll STOP between spans of at most 64 bytes.
    at = 0
    def span(name, size, src, repeated=False, zero=False, word=False):
        nonlocal at
        width = 2 if word else 1
        for verify in (False,True):
            c.emit(0xc2 if word else 0xe2,0x20)
            imm(0xa0,at)
            if zero:
                imm(0xa9,0)
            elif repeated:
                c.long(0xaf,0x400010+src)
            else:
                imm(0xa2,src)
            label = name+("_check" if verify else "_store")
            c.label(label)
            if not (zero or repeated):
                c.long(0xbf,0x400010)
                c.emit(0xe8)
            c.emit(0xd7 if verify else 0x97,0x60)
            if verify:
                c.emit(0xf0,3)
                c.jump("bad_packet")
            c.emit(*([0xc8]*width))
            imm(0xc0,at+size)
            c.branch(0xd0,label)
        service()
        at += size

    for i in range(3):
        span(f"raw984_{i}",64,6+2*i,repeated=True,word=True)
    for i in range(3):
        span(f"table984_{i}",21,12+21*i)
        span(f"pad984_{i}",60,None,zero=True,word=True)
    span("length984",6,0)
    assert at == 441
    c.emit(0xc2,0x20)
    c.jump("accepted")
    body.extend(c.finish())
    assert len(body)<=8192
    # Measure the exact static requirement even if the board ROM is full.
    with patch.object(boot,"STORED",8192):
        boot.build(LOADER_SOURCE,WORK/"client",bytes(body),c.labels,
                   compact_mvn=True,minimum=2,short_pairs=True)
    info=json.loads((WORK/"client/build.json").read_bytes())
    print("Static client ROM",info["loader_B"]+info["encoded_B"],"of",boot.STORED)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--control",action="store_true",help="same extended ROM, original ARM and literal packets")
    a=p.parse_args()
    if a.action=="prepare":
        sender()
        receiver()
    else:
        with patch.object(nes_page963,"PACKED",WORK/"client"):
            arm = baseline("returned") if a.control else WORK
            tag = "984literal" if a.control else "984compact"
            nes_page963.simulate(a.temp,a.phase,"cold",True,arm,True,tag=tag,edition=966)
