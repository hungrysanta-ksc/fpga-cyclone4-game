# SPDX-License-Identifier: MIT
"""Prepare a sealed DMA group's static registers before its fresh VBlank wait."""
import argparse
import hashlib
import json
from pathlib import Path
from build_nes_trace_replay import Code
from nes_head637 import head_map
from nes_rom636 import build
from nes_native_local165 import call

ORIGIN = 0x7e2000


def receiver(body, labels):
    body = bytearray(head_map(body, labels))
    assert hashlib.sha256(body).hexdigest() == 'dc8db1b495328baf5dfdbb959adda660f0692b6be48d3a70028f2147b542f969'
    c = Code(ORIGIN + len(body))
    c.labels.update(labels)
    # service preserves X and the DMA registers: it only checks sticky STOP,
    # invalidates receipts on STOP and forwards a completed joypad sample.
    # SEAL already holds an immutable, independently checked command group.
    # Neither programming DMAP/A1B nor loading X starts DMA or writes VRAM.
    c.label('prepare665')
    c.absolute(0x8e, 0x103a)
    c.emit(0xa9, 1, 0x18); c.absolute(0x8d, 0x4300)
    c.emit(0xe2, 0x20, 0xa9, 0x7f); c.absolute(0x8d, 0x4304)
    c.emit(0xc2, 0x20); c.absolute(0xae, 0x1252)
    call(c, 'wait169')
    c.emit(0xb0, 3); c.jump('upload_return212')
    c.jump('upload_loop212')
    start = labels['group_ready538'] - ORIGIN
    assert body[start:start+3] == bytes.fromhex('8e3a10')
    body[start:start+3] = bytes([0x4c]) + (c.labels['prepare665'] & 65535).to_bytes(2, 'little')
    # After observing entry into VBlank, the counter is dead. Each next wait
    # initializes it before either bounded polling phase. Preserve C=1/RTS.
    end = labels['cancel169'] - ORIGIN
    assert body[end-8:end] == bytes.fromhex('a9ffff8d3e103860')
    body[end-8:end-6] = bytes.fromhex('3860')
    c.labels['wait_success665'] = ORIGIN + end - 8
    return bytes(body) + c.finish(), c.labels


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('base', type=Path)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    symbols = {}
    def edit(body, labels):
        data, new = receiver(body, labels)
        symbols.update(new)
        return data
    build(a.base, a.out, edit_body=edit, allow_extension=True)
    (a.out/'labels.json').write_text(json.dumps(symbols, indent=2)+'\n')
    info = json.loads((a.out/'build.json').read_text())
    info.update(candidate='entry665', independent_validation_unchanged=True,
                final_last_line=246, extra_RAM_B=0, new_protocol=False,
                copy_verified_bytes=info['body_bytes'],
                body_free=info['body_capacity']-info['body_bytes'])
    (a.out/'build.json').write_text(json.dumps(info, indent=2)+'\n')
    print(json.dumps({k:info[k] for k in ('body_bytes','physical_ROM_B','physical_free_B')}))


if __name__ == '__main__':
    main()
