"""Build the MMC860 edition from the qualified 859G sender and 858E client."""
import argparse
import json
import shutil
from pathlib import Path

from nes_raw506 import sha
from prepare_nes_trial802 import PROBES, rename_edition
from prepare_nes_trial816 import fit

ROOT = Path(__file__).resolve().parents[1]
WORK = PROBES / 'nes-trial860'
ARM = PROBES / 'nes-tail859/link-g/src'
CLIENT = PROBES / 'nes-seal858/client-e'


def board(temp):
    parent = json.loads((ROOT/'analysis/trial855-package.json').read_bytes())
    evidence = json.loads((ROOT/'analysis/tail859-results.json').read_bytes())
    base = temp/'nes-trial816-board855'
    dest = temp/'nes-trial816-board860'
    assert sha(base/'output_files/board.sof') == parent['board']['image']['SOF']
    assert sha(CLIENT/'sink165.sfc') == evidence['scenes']['demo']['1']['859g']['client']
    rom = (CLIENT/'sink165.sfc').read_bytes()
    assert bytes.fromhex((CLIENT/'sink-program.hex').read_text()) == rom[:5056]+rom[-64:]
    dest.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(base/sub,dest/sub)
    for file in base.iterdir():
        if file.suffix in ('.v','.sv','.vhd','.qpf','.qsf','.sdc','.hex','.tcl'):
            shutil.copyfile(CLIENT/file.name if file.name=='sink-program.hex' else file,dest/file.name)
    assert sha(dest/'sink-program.hex')==sha(CLIENT/'sink-program.hex')
    fit(temp,860,Path('C:/altera_lite/25.1std/quartus/bin64'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('board','arm'))
    p.add_argument('temp',type=Path)
    a=p.parse_args()
    if a.action=='board':
        board(a.temp)
    else:
        rename_edition(ARM,WORK/'patch',855,860)
