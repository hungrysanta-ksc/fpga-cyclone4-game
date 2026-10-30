# SPDX-License-Identifier: MIT
"""493 ARM-only split with the byte-identical hardware489 FPGA and all restores."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'tools/package_nes_schedule492.py').read_text()
s=s.replace('schedule492-verification','boot493-verification').replace('nes-mmc492-trial','nes-mmc493-trial')
s=s.replace('492','493').replace('MMC493-SCHEDULE.zip','MMC493-BOOT-SPLIT.zip')
exec(compile(s,str(ROOT/'tools/package_nes_schedule492.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/package_nes_schedule492.py')})
