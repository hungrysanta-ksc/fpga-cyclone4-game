# SPDX-License-Identifier: MIT
"""Use the already accepted head map, exposing closed tiles behind it on retirement."""
import argparse
from pathlib import Path
from nes_rom636 import build


def head_map(body, labels):
    # The original reader has X=head here. Only retarget the BEQ after
    # (source & 0x7000)==0x5000. The size cap, STOP/head check, beam and
    # synchronous retire routine remain shared with the existing map path.
    entry=labels['prefix523']
    end=labels['tail532']
    base=0x7e2000
    check=bytes.fromhex('bf00407e290070c90050f0')
    offset=body.index(check,entry-base,end-base)+len(check)
    next_pc=base+offset+1
    assert next_pc+int.from_bytes(body[offset:offset+1],'little',signed=True)==end
    distance=labels['row526']-next_pc
    return body[:offset]+distance.to_bytes(1,'little',signed=True)+body[offset+1:]


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    build(args.base,args.out,edit_body=head_map)
