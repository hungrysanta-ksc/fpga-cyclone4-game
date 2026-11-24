"""Use both words of the accepted OAM repeat instead of copying one byte per MVN step."""
from unittest.mock import patch
import boot_nes_column854 as boot
from build_nes_trace_replay import Code
from check_nes_plan975 import read
from nes_blank959 import ORIGIN, LOADER_SOURCE
from nes_hdma990 import PACKED
from nes_oam992 import ROOT


def build(source=PACKED, name="store"):
    labels=read(source/"labels.json")
    body=bytearray((source/"body.bin").read_bytes())
    start=body.index(bytes.fromhex("8ba67aa57a18690400a8"),labels["literal_length227"]-ORIGIN,labels["repeat_done227"]-ORIGIN)
    end=body.index(bytes.fromhex("ab201936"),start,start+30)+1
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    def imm(op,v):
        c.emit(op);c.word(v)
    c.label("store992")
    c.absolute(0xad,0x120c);imm(0x89,15);c.branch(0xf0,"blocks992")
    c.emit(0x8b,0xa6,0x7a);c.absolute(0x4c,(ORIGIN+start+3)&65535)
    c.label("blocks992")
    c.emit(0x4a,0x4a,0x4a,0x4a,0xa8,0xa6,0x7a)
    c.label("write992")
    # Header, section, four-byte alignment, expansion bounds and cursor were
    # checked by repeat227/data. Keep the queue head owned until all stores finish.
    for half in (0,2):
        c.long(0xaf,0x400010+half)
        for i in range(0,16,4):
            c.long(0x9f,0x7f0000+i+half)
    c.emit(0x8a,0x18);imm(0x69,16);c.emit(0xaa,0x88)
    c.branch(0xf0,"end992");c.emit(0x98);imm(0x29,3);c.branch(0xd0,"write992")
    c.emit(0xda,0x5a);c.absolute(0x20,labels["service"]&65535);c.emit(0x7a,0xfa)
    c.absolute(0xad,0x1236)
    c.branch(0xf0,"write992");c.jump("stop_packet")
    c.label("end992");c.absolute(0x4c,(ORIGIN+end)&65535)
    body[start:start+3]=bytes((0x4c,))+(c.labels["store992"]&65535).to_bytes(2,"little")
    body.extend(c.finish())
    with patch.object(boot,"STORED",5800):
        boot.build(LOADER_SOURCE,ROOT/name,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


if __name__=="__main__":
    build()
