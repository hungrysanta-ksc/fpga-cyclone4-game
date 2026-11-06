# SPDX-License-Identifier: MIT
"""Run the full linked ARM with separate input/export and display generations."""
import argparse
import runpy
import sys
from pathlib import Path
from unittest.mock import patch
import test_nes_tile532 as tile
from nes_raw506 import once
from test_nes_raw506_joint import Runtime


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--commit-pop-bound',action='store_true')
    options,rest=parser.parse_known_args();sys.argv[1:]=rest
    original=tile.run_schedule
    def run(a,instrument,link_type,frames):
        a.early_export=True
        a.commit_pop_bound=options.commit_pop_bound
        def checked(source,args):
            source=instrument(source,args)
            for gen in range(905,905+frames):
                folder=a.capture/f'frame{gen}'
                expected=(folder/'expected-cgram.bin').read_bytes()+(folder/'expected-oam.bin').read_bytes()
                assert len(expected)==1056
                (a.out/f'colors636-{gen}.bin').write_bytes(expected)
            return once(source,'  lastStatus=ack[1];',"""  if pb(0)==3 and ack[1]==1 then
   local bytes=file('colors636-'..pw(8)..'.bin')
   for i=0,511 do assert(emu.read(i,emu.memType.snesCgRam)==(bytes:byte(i+1)&(i%2==1 and 127 or 255)),'CGRAM '..i) end
   for i=0,543 do assert(emu.read(i,emu.memType.snesSpriteRam)==bytes:byte(513+i),'OAM '..i) end
  end
  lastStatus=ack[1];""")
        return original(a,checked,link_type,frames)
    # supply549 imports its run_schedule symbol when executed as __main__.
    with patch.object(tile,'run_schedule',run), patch.object(Runtime,'linked_runtime_storage',True,create=True):
        runpy.run_module('test_nes_board611',run_name='__main__')
