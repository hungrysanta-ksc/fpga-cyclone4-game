# SPDX-License-Identifier: MIT
"""Let the reset-held physical reader drive OE and stage bulk cancel release locally."""
import argparse
from pathlib import Path
from prepare_nes_arg564 import prepare as arg564
from nes_raw506 import once


def prepare(base,out):
    arg564(base,out)
    boot=out/'nes_rom_boot.sv'
    assert "assign load_oe=1'b1;" in (out/'nes_rom_loader.sv').read_text()
    boot.write_text(once(boot.read_text()," assign psram_oe=reset?1'b1:reader_owner?read_oe:load_oe;",
        """ // Only the reader enables OE. When it has no owner, reader_reset
 // asynchronously idles its pins, even if the memory clock is stopped.
 assign psram_oe=read_oe;"""),newline='\n')
    bulk=out/'nes_tile_bulk206.sv'
    s=once(bulk.read_text(),'.raw_reset(cancel),.reset(hc)',
           '.raw_reset(hr||source_failed||host_failed),.reset(hc)')
    bulk.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
