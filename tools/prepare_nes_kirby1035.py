"""MMC1034 A/B. Admit only sealed collector geometry while the old tile plan is open."""
import argparse
import hashlib
import shutil
from pathlib import Path

from prepare_nes_kirby1027 import replace

BASE = Path(__file__).resolve().parents[2] / 'probes/nes-kirby1034/board-shared'
OLD = '(export_permitted204||(lease204&&plan_closed204))&&!direct_nes_fault204'
NEW = '(export_permitted204||(lease204&&(plan_closed204||native_geometry_valid)))&&!direct_nes_fault204'


def prepare(out):
    if hashlib.sha256((BASE/'nes_live_joint.sv').read_bytes()).hexdigest() != '6e33a2878d8dccfe76d25b34a381b6b768eeda803ccd2c14125afcaad54988a8':
        raise ValueError('unexpected MMC1034 board revision')
    shutil.copytree(BASE, out)
    replace(out/'nes_live_joint.sv', '.enable('+OLD+')', '.enable('+NEW+')')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    prepare(parser.parse_args().out)
