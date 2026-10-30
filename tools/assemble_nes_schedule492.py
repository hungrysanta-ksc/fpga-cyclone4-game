# SPDX-License-Identifier: MIT
"""Use491 source-pinned FIT/STA and exact RBF for the492 paired trial."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'tools/assemble_nes_output489.py').read_text()
assert s.count('fpga_mmc489.bi3')==2
s=s.replace('fpga_mmc489.bi3','fpga_mmc492.bi3')
exec(compile(s,str(ROOT/'tools/assemble_nes_output489.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/assemble_nes_output489.py')})
