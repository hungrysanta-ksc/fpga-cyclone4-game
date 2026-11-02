# SPDX-License-Identifier: MIT
"""Keep the checked command cursor and destination live through ordinary SEAL DMA."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_receipt548
from nes_history547 import group
from nes_raw506 import once


def upload(source, early):
    source = group(source, early)
    # wait169 and compact raw service can change X. Normal DMA has no call.
    source = once(source, "c.label('upload_loop212');c.absolute(0xae,0x1252);",
                  "c.absolute(0xae,0x1252);c.label('upload_loop212');")
    first = source.index(" lda(0x1258);c.branch(0xf0,'raw_legacy489')")
    last = source.index("c.emit(0x4a);sta(0x2116)", first)
    source = source[:first] + """ c.long(0xbf,0x7e4002);c.emit(0xc9,0,0x50);c.branch(0xf0,'raw_address550')
 c.emit(0xc9,0,0x90);c.branch(0xd0,'normal_dest550')
 c.label('raw_address550');c.absolute(0xac,0x1258);c.branch(0xf0,'normal_dest550')
 c.label('raw_dispatch489');call(c,'raw_dma489');lda(0x1236);cond(0xd0,'upload_return212')
 c.absolute(0xae,0x1252);c.jump('raw_advance489')
 c.label('raw_legacy489');c.label('normal_dest550');""" + source[last:]
    source = once(source,"sta(0x2116);c.long(0xbf,0x7e4004);sta(0x4305)",
                  "sta(0x2116);c.long(0xbf,0x7e4000);sta(0x4302);c.long(0xbf,0x7e4004);sta(0x4305)")
    return once(source,"c.label('raw_advance489');lda(0x1252);c.emit(0x18,0x69,8,0);sta(0x1252);c.absolute(0xcd,0x103a);",
                "c.label('raw_advance489');c.emit(0x8a,0x18,0x69,8,0,0xaa);c.absolute(0x8e,0x1252);c.absolute(0xec,0x103a);")


def build(out):
    with patch.object(nes_receipt548.history,'group',upload):
        result=nes_receipt548.build(out)
    result.update(candidate='upload550')
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    print(build(p.parse_args().out)['body_bytes'])
