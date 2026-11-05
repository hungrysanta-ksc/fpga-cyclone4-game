"""Use the checked fixed-source fill for uniform palette repeats, without publishing raw receipts."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_admit556
import nes_receipt548
from nes_raw506 import once


def build(out):
    original=nes_receipt548.value_packet
    def palette(source):
        s=original(source)
        s=once(s,"lda(0x1201);c.emit(0xc9,5);c.branch(0xd0,'word516')",
               """lda(0x1201);c.emit(0xc9,3);c.branch(0xf0,'uniform608')
 c.emit(0xc9,5);c.branch(0xd0,'word516')
 c.label('uniform608')""")
        return once(s,"lda(0x60);cond(0xf0,'fill_receipt548');c.emit(0xc9,65,0)",
                    """lda(0x60);c.branch(0xd0,'more608')
 lda(0x1201);c.emit(0x29,255,0,0xc9,3,0);cond(0xf0,'accepted');c.jump('fill_receipt548')
 c.label('more608');c.emit(0xc9,65,0)""")
    with patch.object(nes_receipt548,'value_packet',palette):
        result=nes_admit556.build(out)
    result.update(candidate='quiet608-palette',palette_fixed_chunk_B=64)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    print(build(p.parse_args().out)['body_bytes'])
