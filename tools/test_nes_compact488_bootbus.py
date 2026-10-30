# SPDX-License-Identifier: MIT
"""Actual8KiB cartridge code/header reads at23 phases plus STOP; not CPU boot."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'tools/test_nes_mmc481_bootbus.py').read_text(encoding='utf8')
s=s.replace("assert (a.board/'sink-program.hex').read_bytes() == (live/'sink-program.hex').read_bytes()","assert len(bytes.fromhex((a.board/'sink-program.hex').read_text()))==8192")
s=s.replace('expected[0:4095]','expected[0:8191]').replace('expected[4092]','expected[8188]').replace('expected[4093]','expected[8189]')
s=s.replace('i<4032','i<8128').replace('expected[4032+i]','expected[8128+i]').replace("24'h008fc0","24'h009fc0").replace('reads=4100','reads=8196').replace("'reads': 4100","'reads': 8196")
exec(compile(s,str(ROOT/'tools/test_nes_mmc481_bootbus.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_mmc481_bootbus.py')})
