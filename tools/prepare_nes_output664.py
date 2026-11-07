"""A bounded scroll/padding overlap candidate on the pinned MMC662 ARM."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from nes_raw506 import once


def prepare(base, out, mode='prefix'):
    assert digest(base / 'src/obj-nes-100/firmware.stm') == evidence('trial662-package.json')['firmware_SHA256']
    shutil.copytree(base, out, ignore=shutil.ignore_patterns('obj-*', '.dep-*', '*.log', '*.json'))
    p = out / 'src/nes_native_sink165.c'
    old = 'section==5?NES_HDMA554:NES_ORDINARY553'
    new = ('section==5 && at>=1121?NES_HDMA554:NES_ORDINARY553'
           if mode=='prefix' else 'NES_ORDINARY553')
    s = once(p.read_text(), old, new)
    note = ''' /* The already-final scroll and zero padding use disjoint section-5 WRAM.
  * Offer one packet under the existing ordinary credit policy while a tile
  * retires. Compact raw/table bytes and final SEAL keep the full END gate. */
 if(s->plan && op>=2''' if mode=='prefix' else ''' /* Section-5 payload is immutable at this caller and targets separate WRAM.
  * Use the existing ordinary credit policy for the selected prefix/full range.
  * A ready bulk still wins. Final SEAL always keeps the full END/consume gate. */
 if(s->plan && op>=2'''
    s = once(s, ' if(s->plan && op>=2', note)
    p.write_text(s, newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('base', type=Path)
    p.add_argument('out', type=Path)
    p.add_argument('--mode', choices=('prefix','all'), default='prefix')
    a = p.parse_args()
    prepare(a.base, a.out, a.mode)
