"""Build the FF3 client with an explicit raw-plane constant and pad turbo."""
import argparse
from pathlib import Path

from build_ff3_menu_client import program
from prepare_ff3_scroll1049 import arm
from prepare_nes_kirby1023 import edit


def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    program(out/'client', turbo=True)
    arm(out/'link')
    for name in ('nes_menu_diagnostic.c','nes_checkpoint112.c'):
        edit(out/'link/src',name,('ff31049','ff31050'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path)
    prepare(parser.parse_args().out)
