# SPDX-License-Identifier: MIT
"""491 C/source/ROM/SPI/65816/STOP join; functional RPC, not common-clock timing."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'tools/test_nes_supply485_live.py').read_text(encoding='utf8')
s=s.replace('a=p.parse_args()',"p.add_argument('--client',type=Path,required=True)\np.add_argument('--mesen',type=Path,required=True)\na=p.parse_args()",1)
needle="s=s.replace(needle,extra+'\\n'+needle)"
assert s.count(needle)==1
s=s.replace(needle,"s=s.replace(needle,extra+'\\n'+\"exe=Path(\"+repr(str(a.client.resolve()/'sink165.sfc'))+\");mesen=Path(\"+repr(str(a.mesen.resolve()))+\")\")")
marker="runner.write_text(s,encoding='utf8',newline='\\n')"
assert s.count(marker)==1
s=s.replace(marker,"s=s.replace(\"mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')\",\"mesen=Path(\"+repr(str(a.mesen.resolve()))+\")\")\n"+marker)
exec(compile(s,str(ROOT/'tools/test_nes_supply485_live.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_supply485_live.py')})
