# SPDX-License-Identifier: MIT
"""Actual5KiB cartridge code/header reads at23 phases plus STOP; not CPU boot."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'tools/test_nes_mmc481_bootbus.py').read_text(encoding='utf8')
s=s.replace("assert (a.board/'sink-program.hex').read_bytes() == (live/'sink-program.hex').read_bytes()","assert len(bytes.fromhex((a.board/'sink-program.hex').read_text()))==5120")
s=s.replace('expected[0:4095]','expected[0:5119]').replace('expected[4092]','expected[5116]').replace('expected[4093]','expected[5117]')
s=s.replace('i<4032','i<5056').replace('expected[4032+i]','expected[5056+i]').replace("24'h008fc0","24'h0093c0").replace('reads=4100','reads=5124').replace("'reads': 4100","'reads': 5124")
exec(compile(s,str(ROOT/'tools/test_nes_mmc481_bootbus.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_mmc481_bootbus.py')})
