# SPDX-License-Identifier: MIT
"""Reuse a checked, ACK-bound zero suffix of section 5 in the target WRAM bank."""
import argparse
import hashlib
import json
from pathlib import Path
from build_nes_trace_replay import Code
from nes_head637 import head_map
from nes_native_local165 import call
from nes_rom636 import build

ORIGIN = 0x7e2000
BANK = 0x14e0        # (first offset + 1, one's complement), four bytes per bank
PENDING = 0x14e8
RAW_START = 1121


def receiver(body, labels):
    body = bytearray(head_map(body, labels))
    assert hashlib.sha256(body).hexdigest() == "dc8db1b495328baf5dfdbb959adda660f0692b6be48d3a70028f2147b542f969"
    c = Code(ORIGIN + len(body))
    c.labels.update(labels)

    def intercept(pc, opcode, original, name):
        offset = pc - ORIGIN
        before = bytes.fromhex(original)
        assert body[offset:offset+len(before)] == before
        c.label(name)
        body[offset:offset+len(before)] = bytes([opcode]) + (c.labels[name] & 65535).to_bytes(2,"little") + bytes([0xea])*(len(before)-3)

    intercept(labels["invalidate635"], 0x20, "9c d0 14", "invalidate647")
    for addr in range(BANK, PENDING+2, 2):
        c.absolute(0x9c, addr)
    c.absolute(0x9c, 0x14d0)
    c.emit(0x60)

    intercept(labels["begin"], 0x20, "9c d8 14", "begin647")
    c.absolute(0x9c, PENDING)
    c.absolute(0x9c, 0x14d8)
    c.emit(0x60)

    # Successful SEAL only. X already indexes the independently checked bank.
    publication = bytes.fromhex("ad22129dd014ad24129dd214")
    assert body.count(publication) == 1
    intercept(ORIGIN+body.index(publication)+3, 0x20, "9d d0 14", "publish647")
    c.absolute(0x9d, 0x14d0)
    c.absolute(0xad, PENDING)
    c.absolute(0x9d, BANK)
    c.emit(0x49, 0xff, 0xff)
    c.absolute(0x9d, BANK+2)
    c.emit(0x60)

    # Enter only after the ordinary reader's identity, length, monotonic section
    # offset, bounds and word checks. All earlier writes end at the new start.
    intercept(labels["generic548"], 0x4c, "c2 20 ad 0c 12", "dispatch647")
    c.emit(0xc2, 0x20)
    for addr,value in ((0x1200,0x0505),(0x1234,RAW_START)):
        c.absolute(0xad, addr)
        c.absolute(0xc9, value)
        c.branch(0xd0, "restore647")
    c.long(0xaf, 0x400010)
    c.branch(0xd0, "restore647")
    c.absolute(0xad, 0x120a)
    c.emit(0x1a)
    c.absolute(0x8d, PENDING)
    c.emit(0xda)
    c.absolute(0xad, 0x1034)
    c.absolute(0xcd, 0x1032)
    c.branch(0xf0, "miss647")
    c.emit(0x0a,0x0a,0xaa)
    c.absolute(0xbd,0x14d0)
    c.absolute(0x1d,0x14d2)
    c.branch(0xf0,"miss647")
    c.absolute(0xbd,BANK)
    c.branch(0xf0,"miss647")
    c.absolute(0x5d,BANK+2)
    c.absolute(0xc9,65535)
    c.branch(0xd0,"miss647")
    c.absolute(0xad,PENDING)
    c.absolute(0xdd,BANK)
    c.branch(0x90,"miss647")
    c.emit(0xfa)
    c.label("hit647")
    call(c,"service")
    c.branch(0xf0,"receipt647")
    c.jump("stop_packet")
    c.label("receipt647")
    c.jump("fill_receipt548")
    c.label("miss647")
    c.emit(0xfa)
    c.label("restore647")
    c.absolute(0xad,0x120c)
    c.absolute(0x4c,(labels["generic548"]+5)&65535)
    return bytes(body)+c.finish(),c.labels


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("base",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    symbols={}
    def edit(body,labels):
        data,new=receiver(body,labels)
        symbols.update(new)
        return data
    build(a.base,a.out,edit_body=edit,allow_extension=True)
    (a.out/"labels.json").write_text(json.dumps(symbols,indent=2)+"\n")
