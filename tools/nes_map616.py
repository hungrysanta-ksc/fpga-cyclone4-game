# SPDX-License-Identifier: MIT
"""Bound a larger accepted-map grant by an earlier VBlank start cutoff."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_grant555
import nes_quiet608_client


def build(out, last_line=251):
    # Keep the tile cutoff, map fallback, and pre-MDMA STOP/head reads.
    # Both bounds reserve a longer VBlank tail for the larger DMA.
    with patch.object(nes_grant555.EightRows, 'map_chunk', 1152), patch.object(
            nes_grant555.EightRows, 'map_last_line', last_line):
        result = nes_quiet608_client.build(out)
    result.update(candidate='map616', map_last_line=last_line)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--last-line',type=int,choices=(251,252),default=251)
    args=p.parse_args()
    print(build(args.out,args.last_line)['body_bytes'])
