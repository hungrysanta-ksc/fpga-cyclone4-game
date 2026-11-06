# SPDX-License-Identifier: MIT
"""Patch sparse groups, then verify each reconstructed WRAM row in address order."""
import argparse
from pathlib import Path
from unittest.mock import patch

import nes_group628 as prior

# X indexes the packet while patching. During the checksum pass it is the
# actual WRAM row address. Preserve the packet cursor and the row-end Y.
START = prior.DECODE.index(" c.label('verify628')")
END = prior.DECODE.index(" call(c,'service')", START)
VERIFY = """
 c.label('verify628');c.emit(0x98,0x18,0x69,4,0,0xa8,0x89,63,0)
 c.branch(0xd0,'group628');c.absolute(0x8e,0x1262)
 c.label('sumrow629');c.emit(0x5a,0x98,0x18,0x65,0x7a);sta(0x126a)
 c.emit(0x38,0xe9,64,0,0xaa);lda(0x1266)
 c.label('sumchunk629')
 for word in range(4):
  c.emit(0x18);c.long(0x7f,0x7f0000+word*2);c.emit(0xa8,0x18)
  c.absolute(0x6d,0x1268);sta(0x1268);c.emit(0x98)
 c.emit(0x48,0x8a,0x18,0x69,8,0,0xaa,0x68)
 c.absolute(0xec,0x126a);c.branch(0xd0,'sumchunk629')
 sta(0x1266);c.emit(0x7a)
 c.label('rowend629')
"""


def build(out):
    decoder=prior.DECODE[:START]+VERIFY+prior.DECODE[END:].replace("c.branch(0x90,'row628')","cond(0x90,'row628')")
    with patch.object(prior,'DECODE',decoder):
        prior.build(out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    build(p.parse_args().out)
