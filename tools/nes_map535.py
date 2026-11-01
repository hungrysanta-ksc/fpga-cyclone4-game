# SPDX-License-Identifier: MIT
"""Use up to four accepted rows per map DMA at the MMC533 arbitration point."""
import argparse
import json
from pathlib import Path
from nes_tile532 import PairedMap,build


class FourRows(PairedMap):
    map_chunk=256

    @classmethod
    def map_length(cls,c,label):
        # Same 15-byte footprint as the paired selector. Both pointers and the
        # remaining length already refer to an accepted, contiguous map job.
        c.long(0xbf,0x7e4004)
        c.emit(0xc9,1,1);c.branch(0x90,label+'_tail')
        c.emit(0xa0,0,1);c.branch(0x80,label)
        c.label(label+'_tail');c.emit(0xa8);c.label(label)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=build(a.out,policy=FourRows)
    result['candidate']='map535'
    (a.out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
