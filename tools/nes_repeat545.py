# SPDX-License-Identifier: MIT
"""Extend the existing section 5 fixed-source fill to uniform short repeats >=64B."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_output489
import nes_prefix523
import nes_seal538
import nes_tile532
import nes_window516
from nes_raw506 import once

original_fill = nes_window516.fill_source


def fill_source(source):
    source = original_fill(source)
    source = once(source, """ lda(0x1200);c.emit(0xc9,5);c.branch(0xd0,'word516')
 c.emit(0xc2,0x20);c.long(0xaf,0x400010);c.branch(0xd0,'word16_516')
 lda(0x120c);sta(0x60)""", """ c.long(0xaf,0x400010);c.long(0xcf,0x400011);c.branch(0xd0,'word516')
 c.emit(0x09,0);c.branch(0xf0,'length545')
 lda(0x1200);c.emit(0xc9,5);c.branch(0xf0,'word516')
 c.label('length545');c.emit(0xc2,0x20);lda(0x120c);c.emit(0xc9,64,0);c.branch(0x90,'word16_516')
 c.emit(0x85,0x60)""")
    # Binary 16-bit remaining count minus chunk = remaining + ~chunk + 1.
    # $4305 already holds the transfer length. No temporary store is needed.
    # Set the source bank with A still wide. The adjacent count byte is
    # overwritten by the complete $4305 length before every DMA start.
    source = once(source, "c.emit(0xe2,0x20);c.store(0x4304,0x40);c.emit(0xc2,0x20)",
                  "imm(0x40);sta(0x4304)")
    return once(source, "sta(0x4305);sta(0x62);lda(0x60);c.emit(0x38);c.absolute(0xed,0x62);sta(0x60)",
                "sta(0x4305);c.emit(0x49,0xff,0xff,0x38);c.emit(0x65,0x60,0x85,0x60)")


def build(out):
    with patch.object(nes_window516, 'fill_source', fill_source), \
         patch.object(nes_prefix523, 'upload', lambda s: nes_seal538.group_upload(s, True)), \
         patch.object(nes_output489, 'emit_raw_dma489', nes_seal538.raw_service_inline()):
        result = nes_tile532.build(out, paired=True)
    assert result['body_bytes'] <= result['body_capacity']
    result.update(candidate='repeat545', minimum_uniform_op4=64, maximum_chunk=64)
    (out/'build.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    print(build(parser.parse_args().out)['body_bytes'])
