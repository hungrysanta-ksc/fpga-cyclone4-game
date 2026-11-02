# SPDX-License-Identifier: MIT
"""Issue up to eight already accepted contiguous map rows on the 554 cutoff schedule."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_tile532
import nes_upload550


class EightRows(nes_tile532.PairedMap):
    map_chunk = 512

    @classmethod
    def map_length(cls, c, label):
        # X selects the head/tail chosen by 532. Only the remaining accepted
        # extent is eligible. Partial DMA always retires exactly map_chunk.
        c.long(0xbf, 0x7e4004)
        c.emit(0xc9)
        c.word(cls.map_chunk)
        c.branch(0x90, label)
        c.emit(0xa9)
        c.word(cls.map_chunk)
        c.label(label)
        c.emit(0xa8)


def build(out):
    with patch.object(nes_tile532, 'PairedMap', EightRows):
        result = nes_upload550.build(out)
    result.update(candidate='grant555', map_chunk_B=EightRows.map_chunk)
    (out / 'build.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    print(build(parser.parse_args().out)['body_bytes'])
