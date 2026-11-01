# SPDX-License-Identifier: MIT
"""Copy one held 16-byte packet header to the existing WRAM view with native MVN."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_repeat545
import nes_tile532
from nes_raw506 import once

base_packet = nes_tile532.packet


def header(source):
    source = base_packet(source)
    # At head524 the transport length is valid and A/X/Y are 16-bit.
    # MVN reads $40:0000..000f, writes $00:1200..120f, and leaves DBR=$00
    # as required by the rest of the receiver. No cursor survives this copy.
    return once(source,
                "c.label('header');c.long(0xbf,0x400000);c.absolute(0x9d,0x1200);c.emit(0xe8,0xe8,0xe0,16,0);c.branch(0xd0,'header')",
                "c.label('header');c.emit(0xa0,0,0x12);imm(15);c.emit(0x54,0,0x40)")


def build(out):
    with patch.object(nes_tile532, 'packet', header):
        result = nes_repeat545.build(out)
    result.update(candidate='header546', header_bytes=16)
    (out/'build.json').write_text(json.dumps(result, indent=2)+'\n',encoding='utf8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    print(build(parser.parse_args().out)['body_bytes'])
