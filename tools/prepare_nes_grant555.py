# SPDX-License-Identifier: MIT
"""Keep the previous VBlank available to accepted map DMA by waiting at OAM."""
import argparse
from pathlib import Path

from nes_raw506 import once


def prepare(arm, out):
    name = 'nes_native_sink165.c'
    cutoff = arm / name
    # The producer submits sections in the checked palette/OAM/HDMA order.
    # Both OAM and HDMA must finish the pending END before publishing.
    source = once(cutoff.read_text(), 'section==5?NES_HDMA554',
                  'section>=4?NES_HDMA554')
    out.mkdir(parents=True, exist_ok=False)
    (out / name).write_text(source, newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for arg in ('arm', 'out'):
        parser.add_argument('--' + arg, required=True, type=Path)
    args = parser.parse_args()
    prepare(args.arm, args.out)
