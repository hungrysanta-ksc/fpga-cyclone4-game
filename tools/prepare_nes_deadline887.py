"""Shorten the quiet retry only while waiting for the published SEAL identity."""
from pathlib import Path
import shutil

from check_nes_strip869 import digest
from nes_coverage886 import BASE, WORK as COVERAGE
from nes_raw506 import once

WORK = BASE.parent / 'nes-deadline887'


def prepare():
    src = BASE / 'link-credit/src'
    assert digest(src / 'obj-nes-100/firmware.stm') == 'e17d511726f17ecd68339973ddcde848052a4533e1a19c6588b52bfb4293e13f'
    patch = WORK / 'patch'
    patch.mkdir(parents=True)
    name = 'nes_native_runtime165.c'
    old = 'reason==2 && r->state==NES_NATIVE165_COMPLETE ? 84u*96u : 84u*128u'
    new = 'reason==2 ? 84u*48u : 84u*128u'
    (patch / name).write_text(once((src / name).read_text(), old, new), newline='\n')
    shutil.copytree(COVERAGE / 'client02', WORK / 'client02')


if __name__ == '__main__':
    prepare()
