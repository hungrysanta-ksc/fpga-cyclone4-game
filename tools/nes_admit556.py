# SPDX-License-Identifier: MIT
"""Use the validated section to scale the range and walk both receipt bitmaps."""
import argparse
import json
from functools import partial
from pathlib import Path
from unittest.mock import patch

import nes_grant555
import nes_tile532
from nes_raw506 import once


def admission(source):
    # X is twice the section: BG=0, OBJ=2, map=4. The previous unit scratch
    # contained only 16/32/64. Leave alignment, byte lengths and append unchanged.
    for unit in (16,32,64):
        source=once(source,f'imm({unit});sta(0x66);','')
    start=source.index(" c.label('units212');")
    end=source.index(' # Source and destination addresses',start)
    source=source[:start]+""" c.label('units212');lda(0x64);call(c,'scale556');sta(0x6c)
 lda(0x62);call(c,'scale556');c.emit(0x18);c.absolute(0x6d,0x68);sta(0x6a)
 c.emit(0x29,7,0,0xa8);imm(1)
 c.label('bit_shift212');c.emit(0xc0,0,0);c.branch(0xf0,'bit_ready212');c.emit(0x0a,0x88);c.branch(0x80,'bit_shift212')
 c.label('bit_ready212');sta(0x6e);lda(0x6a);c.emit(0x4a,0x4a,0x4a,0xaa,0x18);c.absolute(0x6d,0x1254);c.emit(0xa8)
 c.label('bits212');c.emit(0xe2,0x20,0xa5,0x6e);c.absolute(0x3c,0x1280);c.branch(0xd0,'duplicate556')
 c.absolute(0x1d,0x1280);c.absolute(0x9d,0x1280);c.emit(0xa5,0x6e);c.absolute(0x19,0x1320);c.absolute(0x99,0x1320)
 # Advance the one-hot mask. On carry the next unit is bit zero of the next byte.
 c.emit(0x06,0x6e);c.branch(0x90,'same_byte556');c.emit(0x26,0x6e,0xe8,0xc8)
 c.label('same_byte556');c.emit(0xc2,0x20,0xc6,0x6c);c.branch(0xd0,'bits212')
"""+source[end:]
    return once(source," c.label('mark_bad212');", """ c.label('scale556');c.emit(0xe0,2,0);c.branch(0x90,'scale_bg556');c.branch(0xf0,'scale_obj556')
 c.emit(0x4a);c.label('scale_obj556');c.emit(0x4a);c.label('scale_bg556');c.emit(0x4a,0x4a,0x4a,0x4a,0x60)
 c.label('duplicate556');c.emit(0xc2,0x20)
 c.label('mark_bad212');""")


def build(out):
    with patch.object(nes_tile532,'merge_emitter',partial(nes_tile532.merge_emitter,admission)):
        result=nes_grant555.build(out)
    result.update(candidate='admit556')
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    print(build(p.parse_args().out)['body_bytes'])
