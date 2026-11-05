# SPDX-License-Identifier: MIT
"""Try one checked inactive VRAM descriptor at a time before a fresh upload blank."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_map616
import nes_output489
import nes_upload550
from nes_raw506 import once


def build(out):
    base = nes_upload550.upload
    def upload(source,early):
        s=base(source,early)
        # group538 follows validation, append of the raw job and shadow preparation.
        # Leave the retained SEAL head in place. No speculative queue retirement.
        s=once(s," imm(4192);sta(0x1256)\n c.label('budget538')",""" c.emit(0xe2,0x20);lda(0x1024);c.branch(0xf0,'fresh8_618')
 lda(0x4212);c.branch(0x10,'fresh8_618')
 c.emit(0xc2,0x20);c.long(0xbf,0x7e4004);c.emit(0xc9,0x81,1);c.branch(0xb0,'fresh618')
 # Exclude raw dispatch even when its compact wire length would fit the cap.
 c.long(0xbf,0x7e4002);c.emit(0xc9,0,0x50);c.branch(0xf0,'fresh618')
 c.emit(0xc9,0,0x90);c.branch(0xf0,'fresh618')
 call(c,'service');lda(0x1236);cond(0xd0,'cancel169')
 c.emit(0xe2,0x20);lda(0x213f);lda(0x213f);c.emit(0x89,0x40);c.branch(0xd0,'fresh8_618')
 c.label('sample618');lda(0x2137);lda(0x213f);c.emit(0x89,0x40);c.branch(0xf0,'fresh8_618')
 lda(0x213d);c.emit(0xeb);lda(0x213d);c.emit(0x29,1);c.branch(0xd0,'fresh8_618')
 c.emit(0xeb,0xc9,225);c.branch(0x90,'fresh8_618');c.emit(0xc9,253);c.branch(0xb0,'fresh8_618')
 lda(0x4212);c.branch(0x10,'fresh8_618')
 lda(0x6001);c.branch(0x30,'fresh8_618')
 c.emit(0xc2,0x20);c.absolute(0x9c,0x1256)
 lda(0x1252);c.emit(0x18,0x69,8,0);sta(0x103a);c.jump('one618')
 c.label('fresh8_618');c.emit(0xc2,0x20)
 c.label('fresh618');c.absolute(0xae,0x1252);imm(4192);sta(0x1256)
 c.label('budget538')""")
        return once(s,"cond(0x90,'upload_return212')\n imm(0x1801)", "cond(0x90,'upload_return212')\n c.label('one618');imm(0x1801)")
    with patch.object(nes_upload550,'upload',upload),patch.object(nes_output489,'PROGRAM_BYTES489',6144):
        r=nes_map616.build(out,252)
    r.update(candidate='oam618',checked_descriptor_cap_B=384,checked_last_line=252,program_ROM_growth_B=2048)
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    build(p.parse_args().out)
