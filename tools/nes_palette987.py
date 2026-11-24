"""Reuse an acknowledged palette independently of OAM and verify WRAM at SEAL."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import boot_nes_column854 as boot
import nes_page963
from build_nes_trace_replay import Code
from nes_blank959 import LOADER_SOURCE, ORIGIN
from nes_blank960 import PACKED
from nes_head980 import baseline
from nes_native_local165 import call
from nes_raw506 import once

WORK=baseline("returned").with_name("nes-palette987")
ROM=WORK/"rom"


def receiver():
    labels=json.loads((PACKED/"labels.json").read_bytes())
    body=bytearray((PACKED/"body.bin").read_bytes())
    def place(c,start,end):
        data=c.finish()
        assert len(data)<=end-start
        body[start-ORIGIN:end-ORIGIN]=data.ljust(end-start,b'\xea')
    start,end=labels["reuse635"],labels["remaining635"]
    c=Code(start);c.labels.update(labels)
    # DBR is unchanged. Y selects the last ACK for the target bank,
    # X selects the serial in the original or the palette-only command.
    def lda(addr):c.absolute(0xad,addr)
    def cmp(value):c.emit(0xc9);c.word(value)
    def bad():c.branch(0xd0,"bad987")
    lda(0x1034);c.absolute(0xcd,0x1032);c.branch(0xf0,"bad987")
    c.emit(0x0a,0x0a,0xa8);lda(0x1088);bad();lda(0x120e);bad()
    lda(0x1200);cmp(0x0309);c.branch(0xf0,"pal987")
    cmp(0x0409);bad();lda(0x1086);c.absolute(0x0d,0x120a);bad()
    lda(0x120c);cmp(116);bad();c.emit(0xa2,112,0);c.branch(0x80,"id987")
    c.label("bad987");c.jump("bad_packet")
    hole=ORIGIN+body.index(bytes([0xea])*42,labels["compare635"]-ORIGIN,labels["save635"]-ORIGIN)
    c.label("pal987");c.labels["shape987"]=hole;c.jump("shape987")
    c.label("id987");c.long(0xbf,0x400010);c.long(0x1f,0x400012);c.branch(0xf0,"bad987")
    for off in (0,2):
        c.long(0xbf,0x400010+off);c.absolute(0xd9,0x14d0+off);bad()
    extension=ORIGIN+len(body)
    c.labels["finish987"]=extension
    c.emit(0xe0,0,0);c.branch(0xd0,"remaining635");c.jump("finish987")
    place(c,start,end)
    dispatch=c.labels.copy()
    c=Code(hole);c.labels.update(dispatch)
    for addr,value in ((0x1086,32),(0x120a,32),(0x120c,4)):
        lda(addr);cmp(value);c.branch(0xd0,"reject987")
    c.emit(0xa2,0,0);c.jump("id987");c.label("reject987");c.jump("bad_packet")
    place(c,hole,hole+42)
    c=Code(extension);c.labels.update(labels)
    c.emit(0xa9,0xfe,0xff);c.absolute(0x8d,0x14da)
    c.emit(0xa9,0,2);c.absolute(0x8d,0x1086);c.jump("accepted194")
    c.label("seal987");c.absolute(0xad,0x14da);c.emit(0xc9,0xfe,0xff);c.branch(0xd0,"normal987")
    c.emit(0xa2,0,0)
    c.label("chunk987");call(c,"service");c.branch(0xf0,"read987");c.jump("stop_packet")
    c.label("read987");c.long(0xbf,0x7f6000);c.long(0xdf,0x7fe000);c.branch(0xf0,"next987");c.jump("bad_packet")
    c.label("next987");c.emit(0xe8,0xe8,0x8a,0x89,63,0);c.branch(0xd0,"read987")
    c.emit(0xe0,0,2);c.branch(0xd0,"chunk987")
    c.label("normal987");c.absolute(0xad,0x1200);c.labels["resume"]=labels["seal"]+3;c.jump("resume")
    body.extend(c.finish())
    pos=labels["seal"]-ORIGIN
    assert body[pos:pos+3]==bytes.fromhex("ad0012")
    body[pos:pos+3]=b'\x4c'+(c.labels["seal987"]&65535).to_bytes(2,"little")
    labels.update({k:v for k,v in c.labels.items() if k.endswith("987")})
    # Diagnose the complete path when the real 5,056-byte program space
    # overflows. The checker reports occupied bytes with vectors included.
    with patch.object(boot,"STORED",5500):
        boot.build(LOADER_SOURCE,ROM,bytes(body),labels,compact_mvn=True,minimum=2,short_pairs=True)


def prepare():
    dest=WORK/"link"
    shutil.copytree(baseline("returned")/"link",dest)
    h=dest/"src/nes_native_sink165.h"
    h.write_text(once(h.read_text(),"uint8_t disable_column;","uint8_t disable_column,palette_run987;"),newline="\n")
    f=dest/"src/nes_native_sink165.c"
    s=once(f.read_text()," bool same=same635(s,p);",""" bool palette_same=s->displayed&&!memcmp(s->palette635,p->cgram,512);
 bool same=same635(s,p);""")
    s=once(s," if(p->prefix_sent972){",""" if(p->prefix_sent972 && s->palette_run987==2 && palette_same){
  uint32_t owner=s->serial-2;
  if(!packet(s,9,3,32,(const uint8_t *)&owner,4))return false;
 }else if(p->prefix_sent972){""")
    s=once(s," s->ack635[bank]=s->serial;",""" s->palette_run987=palette_same?2:1;
 s->ack635[bank]=s->serial;""")
    f.write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("arm","rom","run","control"));p.add_argument("temp",type=Path);p.add_argument("--phase",type=int,choices=(1,2))
    a=p.parse_args()
    if a.action=="arm":prepare()
    elif a.action=="rom":receiver()
    else:
        with patch.object(nes_page963,"PACKED",ROM):
            case=WORK if a.action=="run" else baseline("returned")
            nes_page963.simulate(a.temp,a.phase,"cold",True,case,True,
                                 tag="987palette" if a.action=="run" else "987control",edition=966)
