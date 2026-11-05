# SPDX-License-Identifier: MIT
"""Compare late accepted-tile service and an independent SEAL coverage walk on 618."""
import argparse
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import nes_admit556
import nes_grant555
import nes_oam618


def late(cls, c, defer):
    c.emit(0xc9, 233); c.branch(0x90, 'map_beam_ok526')
    c.emit(0xc9, cls.map_last_line + 1); c.branch(0xb0, defer)
    c.long(0xbf, 0x7e4001); c.emit(0x29, 0x70, 0xc9, 0x50); c.branch(0xf0, 'map_beam_ok526')
    # Preserve the selected tile while looking for a higher priority map.
    c.emit(0xda, 0xc2, 0x20); c.absolute(0xad, 0x1250); c.emit(0x38, 0xe9, 8, 0, 0xaa)
    c.long(0xbf, 0x7e4000); c.emit(0x29, 0, 0x70, 0xc9, 0, 0x50); c.branch(0xd0, 'tile619')
    c.emit(0x68)  # discard saved X, retain the map tail
    cls.map_length(c, 'fallback_length532'); c.branch(0x80, 'width619')
    c.label('tile619'); c.emit(0xfa, 0xc0, 0x81, 1); c.branch(0x90, 'width619')
    c.emit(0xe2, 0x20); c.branch(0x80, defer)
    c.label('width619'); c.emit(0xe2, 0x20); c.label('map_beam_ok526')


def coverage(source):
    start = source.index(" c.label('coverage_loop212');")
    end = source.index(" c.emit(0x8a,0x18);c.absolute(0x6d,0x1254);c.emit(0xaa)", start)
    # Same 72 words of required slots versus the independently accumulated bank
    # bitmap. X exits at 144 as required by the following map coverage check.
    return source[:start] + """ c.absolute(0xac,0x1254)
 c.label('coverage_loop212')
 for offset in range(0,16,2):
  c.absolute(0xb9,0x1320+offset);c.emit(0x49,255,255);c.long(0x3f,0x400028+offset);c.branch(0xd0,'missing619')
 c.emit(0x98,0x18,0x69,16,0,0xa8,0x8a,0x18,0x69,16,0,0xaa,0xe0,144,0);c.branch(0xd0,'coverage_loop212')
 c.branch(0x80,'covered619');c.label('missing619');c.jump('mark_bad212');c.label('covered619')
""" + source[end:]


def build(out, mode):
    admission = nes_admit556.admission
    with ExitStack() as stack:
        if mode in ('tile', 'both'):
            stack.enter_context(patch.object(nes_grant555.EightRows, 'late_beam', classmethod(late)))
        if mode in ('coverage', 'both'):
            stack.enter_context(patch.object(nes_admit556, 'admission', lambda s: coverage(admission(s))))
        nes_oam618.build(out)
    path = out / 'build.json'
    result = json.loads(path.read_text())
    result.update(candidate='tile619', mode=mode)
    path.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--mode', choices=('coverage', 'tile', 'both'), required=True)
    args = parser.parse_args()
    build(args.out, args.mode)
