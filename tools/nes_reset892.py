"""Rebuild the unmodified 891E board and prepare the bounded pre-release ARM check."""
import argparse
from pathlib import Path
import shutil

from nes_raw506 import once
from package_nes_trial872 import PROBES, ROOT, QUARTUS, fit, read, sha
from prepare_nes_trial802 import rename_edition

WORK=PROBES/'nes-reset892'
BASE=PROBES/'nes-trial891/link-credit'


def board(temp):
    src=temp/'nes-trial816-board891E'
    out=temp/'nes-trial816-board892'
    assert sha(src/'output_files/board.sof')==read(ROOT/'analysis/trial891-package.json')['board']['image']['SOF']
    out.mkdir()
    for name in ('rtl','sys'):
        shutil.copytree(src/name,out/name)
    for path in src.iterdir():
        if path.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.hex','.tcl'):
            shutil.copyfile(path,out/path.name)
    fit(temp,892,QUARTUS)


def arm():
    patch=WORK/'patch'
    rename_edition(BASE/'src',patch,891,892)
    run=(BASE/'src/nes_run136.inc').read_text()
    run=once(run,'static bool screen146(','static unsigned screen146(')
    run=once(run,'nes_run136.screen_flags|=rx[4];nes_run136.screen_frames=((uint16_t)rx[5]<<8)|rx[6];\n return true;',
             'nes_run136.screen_flags|=rx[4];nes_run136.screen_frames=((uint16_t)rx[5]<<8)|rx[6];\n return 0x100u|rx[4];')
    (patch/'nes_run136.inc').write_text(run,newline='\n')
    start=(BASE/'src/nes_startup222.inc').read_text()
    # SPI73 is independent of host_ready. /WR is allowed to remain low
    # until RESET release. Keep the existing post-release E0 and CRC.
    start=once(start,' nes_startup222.ticks=getticks()-started;', ''' if(nes_startup222.reason==NES_STARTUP222_NO_RESPONSE){
  for(unsigned remaining=64;remaining;remaining--){
   unsigned status=screen146(io);
   if(status&0x40)break;
   if(!status||remaining==1){nes_startup222.reason=NES_STARTUP222_GUARD;break;}
  }
 }
 nes_startup222.ticks=getticks()-started;''')
    (patch/'nes_startup222.inc').write_text(start,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['board','arm'])
    p.add_argument('temp',type=Path,nargs='?')
    a=p.parse_args()
    if a.action=='board':
        board(a.temp)
    else:
        arm()
