"""Merge the acknowledged bank's tile receipts in 32-bit groups."""
import shutil

from check_nes_strip869 import digest
from nes_coverage886 import BASE, WORK as COVERAGE
from nes_raw506 import once

WORK = BASE.parent/'nes-history888'


def prepare():
    src = BASE/'link-credit/src'
    assert digest(src/'obj-nes-100/firmware.stm') == 'e17d511726f17ecd68339973ddcde848052a4533e1a19c6588b52bfb4293e13f'
    patch = WORK/'patch'
    patch.mkdir(parents=True)
    name = 'nes_resident211.c'
    original = (src/name).read_text()
    assert '#include <string.h>' in original
    old = ' for(unsigned i=0;i<NES_RESIDENT211_BITS;i++)s->resident[bank][i]|=s->dirty[i];'
    new = ''' _Static_assert(NES_RESIDENT211_BITS % sizeof(uint32_t) == 0, "whole receipt words");
 for (unsigned i=0; i<NES_RESIDENT211_BITS; i+=sizeof(uint32_t)) {
  uint32_t resident, dirty;
  memcpy(&resident, s->resident[bank]+i, sizeof resident);
  memcpy(&dirty, s->dirty+i, sizeof dirty);
  resident |= dirty;
  memcpy(s->resident[bank]+i, &resident, sizeof resident);
 }'''
    (patch/name).write_text(once(original,old,new),newline='\n')
    shutil.copytree(COVERAGE/'client02', WORK/'client02')


if __name__ == '__main__':
    prepare()
