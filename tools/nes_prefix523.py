# SPDX-License-Identifier: MIT
"""Issue at most one closed inactive-bank command at a validated packet boundary."""
import argparse
import json
from pathlib import Path

from nes_native_local165 import call
from nes_raw506 import once
from nes_window516 import build, emit_final516


def emit(c, before_beam=None, before_start=None, rows=None):
    emit_final516(c)
    def load(a): c.absolute(0xad,a)
    def save(a): c.absolute(0x8d,a)
    def branch_far(op,label):
        c.emit(op^0x20,3)
        c.jump(label)
    c.label('prefix523')
    # The open last entry may still be extended by append212. The cursor
    # advances only after synchronous MDMAEN returns, never at admission.
    load(0x1024);c.emit(0x29,255,0);branch_far(0xf0,'skip523')
    load(0x1034);c.absolute(0xcd,0x1032);branch_far(0xf0,'skip523')
    if rows:
        rows.select(c)
    else:
        c.absolute(0xae,0x1252);c.emit(0x8a,0x18,0x69,8,0)
        c.absolute(0xcd,0x1250);branch_far(0xb0,'skip523')
        c.long(0xbf,0x7e4004);c.emit(0xc9,1,8);branch_far(0xb0,'skip523')
    # A fresh beam sample limits this single <=2048-byte DMA. No SEAL
    # credit is granted here. A later packet must recheck the beam.
    if before_beam:
        before_beam(c)
    defer = 'defer_beam' if before_start else 'skip8_523'
    c.emit(0xe2,0x20);load(0x4212);c.branch(0x10,defer)
    load(0x213f);load(0x213f);c.emit(0x89,0x40);c.branch(0xd0,defer)
    load(0x2137);load(0x213f);c.emit(0x89,0x40);c.branch(0xf0,defer)
    load(0x213d);c.emit(0xeb);load(0x213d);c.emit(0x29,1);c.branch(0xd0,defer)
    c.emit(0xeb,0xc9,225);c.branch(0x90,defer)
    if rows and rows.late_beam:
        rows.late_beam(c,defer)
    else:
        c.emit(0xc9,233);c.branch(0xb0,defer)
    load(0x4212);c.branch(0x10,defer)
    if before_start:
        c.branch(0x80,'beam_ok');c.label(defer);c.emit(0xc2,0x20,0x38,0x60);c.label('beam_ok')
    c.emit(0xc2,0x20);c.label('check523');call(c,'service');load(0x1236)
    if rows:
        branch_far(0xd0,'stop523')
    else:
        c.branch(0xd0,'stop523')
    if not rows:
        c.absolute(0xae,0x1252)
    c.label('issue523')
    c.emit(0xa9,1,0x18);save(0x4300)
    c.long(0xbf,0x7e4000);save(0x4302)
    c.emit(0xa9,0x7f,0);save(0x4304)
    if rows:
        c.emit(0x98)  # TYA: selected transfer length
    else:
        c.long(0xbf,0x7e4004)
    save(0x4305)
    c.long(0xbf,0x7e4002);c.emit(0x4a);save(0x2116)
    c.emit(0xe2,0x20);c.store(0x2115,0x80)
    if before_start:
        before_start(c)
    c.store(0x420b,1);c.emit(0xc2,0x20)
    if rows:
        rows.retire(c)
    else:
        load(0x1252);c.emit(0x18,0x69,8,0);save(0x1252)
    call(c,'service');load(0x1236);c.branch(0xd0,'stop523')
    c.label('skip8_523');c.emit(0xc2,0x20)
    c.label('skip523');c.emit(0x38,0x60)
    c.label('stop523');c.emit(0x18,0x60)


def packet(s):
    s=once(s,"c.absolute(0x9c,0x1250)","c.absolute(0x9c,0x1250);c.absolute(0x9c,0x1252)")
    return once(s,"c.label('accepted');lda(0x1200);","c.label('accepted');call(c,'prefix523');cond(0x90,'stop_packet');lda(0x1200);")


def upload(s):
    return once(s,"c.absolute(0x9c,0x1252);c.absolute(0x9c,0x1256)","c.absolute(0x9c,0x1256)")


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result = build(a.out, emitter=emit, fill=True, packet_edit=packet, upload_edit=upload)
    result.update(candidate='prefix523', prefix_last_line=232, prefix_max_bytes=2048, prefix_per_packet=1)
    (a.out / 'build.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(result['body_bytes'])
