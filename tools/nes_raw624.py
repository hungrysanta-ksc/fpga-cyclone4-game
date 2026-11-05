# SPDX-License-Identifier: MIT
"""Emit only the three dirty DMA rows when independent warm receipts certify their partners."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_history547
import nes_tile619
from nes_raw506 import once


def specialize(source):
    # prepare547 starts with zero and sets the six-bit mask only for a 384-byte
    # decoded payload and a committed warm target bank. Bit 0 is the first row.
    source = once(source, "c.label('raw_dma489');c.emit(0x4a)", """c.label('raw_dma489')
    c.absolute(0xac,0x78);c.emit(0xc0,0x15,0);c.branch(0xd0,'generic624');c.jump('pairs624')
    c.label('generic624');c.emit(0x4a)""")
    return once(source, "    c.label('raw_boot489')", """    c.label('pairs624');c.emit(0x4a);sta(0x76)
    imm(0x1801);sta(0x4300);imm(0x7f);sta(0x4304)
    c.emit(0xe2,0x20);c.store(0x2115,0x81);c.emit(0xc2,0x20)
    for pair in range(3):
        # A skipped, certified row performs no DMA. The original service and
        # sticky STOP check precede every 64 bytes that can reach the PPU.
        c.label('row624_'+str(pair))
        call(c,'service');lda(0x1236);cond(0xd0,'raw_stop489')
        lda(0x1020);c.emit(0x18,0x69);c.word(0x6961+64+128*pair);sta(0x4302)
        lda(0x76);c.emit(0x18,0x69);c.word(1+8*pair);sta(0x2116)
        imm(64);sta(0x4305);c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
    c.emit(0x64,0x78);c.jump('raw_return489')
    c.label('raw_boot489')""")


def build(out):
    original = nes_history547.original_raw
    def combined(history_edit):
        return original(lambda source: specialize(history_edit(source)))
    with patch.object(nes_history547, 'original_raw', combined):
        nes_tile619.build(out, 'coverage')
    path = out/'build.json'
    result = json.loads(path.read_text())
    result.update(candidate='raw624', certified_mask=0x15, raw_DMA_B=[64]*3)
    path.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out', type=Path)
    build(p.parse_args().out)
