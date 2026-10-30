# SPDX-License-Identifier: MIT
"""Current488 C/8KiB board -> real source/ROM/SPI/65816/VBlank/STOP join.

First boot display is no-raw; raw decode/DMA is tested separately using actual
M4 captures. Functional RPC has no common physical ARM/IRQ timeline.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'tools/test_nes_supply485_live.py').read_text(encoding='utf8')
s=s.replace('a=p.parse_args()',"p.add_argument('--client',type=Path,required=True)\na=p.parse_args()",1)
old="s=s.replace(needle,extra+'\\n'+needle)"
assert s.count(old)==1
s=s.replace(old,"s=s.replace(needle,extra+'\\n'+\"exe=Path(\"+repr(str(a.client.resolve()/'sink165.sfc'))+\")\")")
exec(compile(s,str(ROOT/'tools/test_nes_supply485_live.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_supply485_live.py')})
