"""Relink 924 objheader for the 60-second Adventure Island 4 trial."""
import argparse
import shutil
from pathlib import Path

from assemble_nes_trial792 import replace_client
from nes_return920 import client, guards
from nes_obj923 import obj_stops
from nes_raw506 import once
from nes_window924 import WORK as CANDIDATES, replay
from package_nes_trial704 import read, sha
from prepare_nes_supply905 import PROBES, QUARTUS, rename_edition

ROOT = Path(__file__).resolve().parents[1]
WORK = PROBES / 'nes-trial925'
ORIGINAL = CANDIDATES / 'objheader'


def prepare():
    reference = read(ROOT/'analysis/window924-results.json')['proof']['objheader']['recovery']
    assert sha(ORIGINAL/'link/src/obj-nes-100/firmware.stm') == reference['firmware']
    assert sha(client('first')/'sink165.sfc') == reference['consumer']
    src = WORK/'link/src'
    shutil.copytree(ORIGINAL/'link', src.parent)
    patch = WORK/'patch'
    rename_edition(src, patch, 915, 925)
    for file in patch.iterdir():
        shutil.copyfile(file, src/file.name)
    budget = src/'nes_budget210.c'
    budget.write_text(once(budget.read_text(), 'log900p->edition=915;', 'log900p->edition=925;'), newline='\n')


def board(temp):
    base = temp/'nes-port914I/nes-trial816-board914'
    parent = read(ROOT/'analysis/trial915-package.json')
    assert sha(base/'output_files/board.sof') == parent['board']['image']['SOF']
    out = temp/'nes-board925'
    out.mkdir(exist_ok=True)
    replace_client(925, base, out, QUARTUS, client('first'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare','board','replay','proof','guards'))
    p.add_argument('temp', type=Path, nargs='?')
    p.add_argument('phase', type=int, choices=(1,2), nargs='?')
    p.add_argument('--cold', action='store_true')
    a = p.parse_args()
    if a.action=='prepare':
        prepare()
    elif a.action=='board':
        board(a.temp)
    elif a.action=='replay':
        replay(a.temp, 'objheader', a.phase, a.cold, arm=WORK, edition=925, tag='925final')
    elif a.action=='guards':
        guards(a.temp,'first',tag='925final',destination=WORK/'final-guards.json')
        obj_stops(a.temp,'first',tag='925final',destination=WORK/'final-stops.json')
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',WORK,925,short_header=True)
