"""Wait for a map DMA progress edge only when the first page has a gap."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base, patch):
    assert digest(base / 'obj-nes-100/firmware.stm') == 'bc45ee5f2a6d1ee35f3cd86a35034a4481987ad22a2b30ccfb755d1fd291ad1b'
    name = 'nes_native_sink165.c'
    src = once((base / name).read_text(), 'if(!wait_map880(w,96))return fail(s,5);',
               '''/* A contiguous prefix needs only its checked credit receipt. */
   uint32_t rows=(uint32_t)map;
   unsigned reads=(rows & (rows+1u)) ? 96u : 1u;
   if(!wait_map880(w,reads))return fail(s,5);''')
    patch.mkdir(parents=True)
    (patch / name).write_text(src, newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('patch', type=Path)
    prepare(**vars(parser.parse_args()))
