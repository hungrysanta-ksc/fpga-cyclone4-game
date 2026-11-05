# SPDX-License-Identifier: MIT
"""Take the suffix of an accepted map descriptor when the idle grant is partial."""
import argparse
import inspect
import json
from pathlib import Path
from unittest.mock import patch

import nes_grant555
import nes_prefix523
import nes_raw624
from nes_raw506 import once


def build(out):
    source = inspect.getsource(nes_prefix523.emit)
    source = once(source, '    c.long(0xbf,0x7e4000);save(0x4302)', '''    # All tile grants take the whole descriptor. A partial map takes the last
    # 1152 bytes, leaving the original source/destination of its prefix intact.
    c.emit(0x98);c.long(0xdf,0x7e4004);c.branch(0xf0,'whole_address626')
    c.long(0xbf,0x7e4004);c.emit(0x38,0xe9);c.word(rows.map_chunk);c.emit(0x48)
    c.emit(0x18);c.long(0x7f,0x7e4000);save(0x4302)
    c.emit(0x68,0x18);c.long(0x7f,0x7e4002);c.branch(0x80,'dest626')
    c.label('whole_address626');c.long(0xbf,0x7e4000);save(0x4302)
    c.long(0xbf,0x7e4002);c.label('dest626');c.emit(0x4a);save(0x2116)''')
    source = once(source, '    c.long(0xbf,0x7e4002);c.emit(0x4a);save(0x2116)\n', '')
    ns = dict(vars(nes_prefix523))
    exec(compile(source, 'map626-idle-address', 'exec'), ns)
    from nes_map526 import MapRows
    retire = inspect.getsource(MapRows.retire)
    start = retire.index('        for address in')
    end = retire.index('        c.long(0xbf,0x7e4004)', start)
    # Only shrink the remaining prefix after synchronous MDMAEN returns.
    import textwrap
    exec(textwrap.dedent(retire[:start] + retire[end:]), ns)
    with patch.object(nes_prefix523, 'emit', ns['emit']), patch.object(nes_grant555.EightRows, 'retire', ns['retire']):
        nes_raw624.build(out)
    path = out/'build.json'
    metadata = json.loads(path.read_text())
    metadata.update(candidate='map626', partial_map='suffix')
    path.write_text(json.dumps(metadata, indent=2)+'\n')


def build_whole(out,after_selection=False):
    original=nes_grant555.EightRows.late_beam.__func__
    def select_size(cls,c,defer):
        if after_selection:
            nes_prefix523.call(c,'late_select626')
            c.branch(0xb0,defer)
            return
        nes_prefix523.call(c,'whole_size626')
        original(cls,c,defer)
    emitter=nes_prefix523.emit
    def emit(c,*args):
        emitter(c,*args)
        if after_selection:
            # M=8 at both exits. Retain the latched scanline across the real
            # late tile-to-map fallback and unwind it on all deferrals.
            c.label('late_select626');c.emit(0x48)
            original(nes_grant555.EightRows,c,'defer_select626')
            c.emit(0x68);nes_prefix523.call(c,'whole_size626');c.emit(0x18,0x60)
            c.label('defer_select626');c.emit(0x68,0x38,0x60)
        # The beam was latched with M=8. The index registers remain 16-bit.
        # A partial selection of 1152 implies a map. Allow its exact 1344B
        # extent only on an earlier line. No other partial length can retire.
        c.label('whole_size626');c.emit(0xc0);c.word(1152);c.branch(0xd0,'ordinary626')
        c.emit(0xc9,248);c.branch(0xb0,'ordinary626')
        c.emit(0x48,0xc2,0x20);c.long(0xbf,0x7e4004)
        c.emit(0xc9);c.word(1344);c.branch(0xd0,'restore626')
        c.emit(0xa8)
        c.label('restore626');c.emit(0xe2,0x20,0x68);c.label('ordinary626')
        c.emit(0x60)
    with patch.object(nes_grant555.EightRows,'late_beam',classmethod(select_size)), patch.object(nes_prefix523,'emit',emit):
        nes_raw624.build(out)
    path=out/'build.json'
    metadata=json.loads(path.read_text())
    metadata.update(candidate='map626-whole',whole_map_B=1344,whole_last_line=247,after_selection=after_selection)
    path.write_text(json.dumps(metadata,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    p.add_argument('--whole',action='store_true')
    p.add_argument('--after-selection',action='store_true')
    args=p.parse_args()
    if args.whole or args.after_selection:
        build_whole(args.out,args.after_selection)
    else:
        build(args.out)
