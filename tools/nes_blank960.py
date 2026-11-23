"""Boot the exact 959 retry body from a compact, independently verified stream."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_chr951
from nes_blank959 import ROM, LOADER_SOURCE, OUT, WORK, build, edits
from nes_ready958 import complete_row_set, feedback, replay, supply
from nes_companion952 import project
from prepare_nes_frame900 import QUARTUS, fit

PACKED = OUT.parents[1]/'nes-blank960'/'retry'


def prepare():
    body=bytearray((ROM/'body.bin').read_bytes())
    for offset,old,new in edits('retry'):
        assert body[offset]==old
        body[offset]=new
    build(LOADER_SOURCE,PACKED,bytes(body),json.loads((ROM/'labels.json').read_bytes()),
          compact_mvn=True,minimum=2,short_pairs=True)


def fit_board(temp):
    old=project(temp,'checked')
    assert (old/'sink-program.hex').read_bytes()==(ROM/'sink-program.hex').read_bytes()
    target=temp/'nes-trial816-board960'
    target.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(old/sub,target/sub)
    for p in old.iterdir():
        if p.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.tcl','.hex'):
            src=PACKED/p.name if p.name=='sink-program.hex' else p
            shutil.copyfile(src,target/p.name)
    fit(temp,960,QUARTUS)


def run(mode,temp,phase,cache):
    with patch.object(nes_chr951,'ROM',ROM if mode=='control' else PACKED):
        if mode in ('static','control'):
            with complete_row_set():
                replay(temp,phase,cache,'banked',wrap=lambda base:supply(base,'checked'),
                       tag='960'+mode,work_arm=WORK,edition=955)
        else:
            assert cache=='cold'
            feedback(temp,phase,close=mode=='closed',trial_tag='960'+mode,
                     baseline_tag='960static',credit_tag='960credit')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('prepare','fit','control','static','credit','closed'))
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,nargs='?',choices=(1,2))
    p.add_argument('--cache',choices=('warm','cold'),default='cold')
    a=p.parse_args()
    if a.mode=='prepare':
        prepare()
    elif a.mode=='fit':
        fit_board(a.temp)
    else:
        run(a.mode,a.temp,a.phase,a.cache)
