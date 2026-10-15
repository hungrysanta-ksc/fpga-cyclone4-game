# SPDX-License-Identifier: MIT
"""Candidate SNES client: publish one coherent joypad snapshot per active field.

Protocol1815, video code and FPGA remain unchanged. Not a deployable package.
The auto-reader may start AFTER vblank becomes true; an idle flag at vblank
entry is not a completion witness. Keep the old held level until a snapshot
has been read and rechecked outside vblank/busy. No debounce or edge filter.
"""
from pathlib import Path
import argparse, inspect, json
import nes_stream181 as stream
from nes_clip178 import replace


def source181(s):
    s = stream.source181(s)
    start = s.index(" c.label('service_pad');")
    end = s.index(" c.label('service_done');", start)
    return s[:start] + """ c.label('service_pad');lda(0x4212);c.emit(0x29,0x81);c.branch(0xf0,'pad_active185')
 c.store(0x1238,0);c.branch(0x80,'service_done')
 c.label('pad_active185');lda(0x1238);c.branch(0xd0,'service_done')
 # Stack holds both bytes until the second timing check. Never publish a
 # partial read; 16-bit STA writes low then high (the existing commit byte).
 c.emit(0xc2,0x20);lda(0x4218);c.emit(0x48,0xe2,0x20)
 lda(0x4212);c.emit(0x29,0x81);c.branch(0xd0,'pad_discard185')
 c.emit(0xc2,0x20,0x68);sta(0x6002);c.emit(0xe2,0x20)
 c.store(0x1238,1);c.branch(0x80,'service_done')
 c.label('pad_discard185');c.emit(0xc2,0x20,0x68,0xe2,0x20)
""" + s[end:]


def build(out):
    # Reuse the selected production generator and its branch relaxation.
    ns = dict(stream.__dict__)
    ns['source181'] = source181
    exec(compile(inspect.getsource(stream.build), 'pad185-build', 'exec'), ns)
    result = ns['build'](out)
    result.update(scope=__doc__,candidate='pad185',extra_persistent_ram=0,
                  extra_stack_bytes=2,physical=False,hardware_package=False)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(build(p.parse_args().out),indent=2))
