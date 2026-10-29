# SPDX-License-Identifier: MIT
"""Run 415 representative RTL prefix using the exact 424 visual fixture."""
import argparse,sys
from pathlib import Path
from nes_delta231 import ROOT
p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
rom=a.rom.resolve();raw=rom.read_bytes();assert len(raw)==24592 and raw[:6]==b'NES\x1a\x01\x01'
s=(ROOT/'tools/test_nes_nrom415_wiring.py').read_text()
def once(s,x,y):assert s.count(x)==1,(x,s.count(x));return s.replace(x,y)
s=once(s,"a.fixture/'run03-loader.c'","a.fixture/'fixture424-loader01-loader.c'")
anchor="bench=(ROOT/'tests/nes-nrom410/prefix_tb.sv').read_text()"
extra='''
assert bench.count('reg clk=0,mem_clk=0,reset=1;')==1
assert bench.count("if(actual!==8'((i+16)^((i+16)>>8)^8'ha5))")==1
bench=bench.replace('reg clk=0,mem_clk=0,reset=1;', 'reg [7:0] expected424[0:255]; initial $readmemh("fixture424-prg.hex",expected424);\\n reg clk=0,mem_clk=0,reset=1;')
bench=bench.replace("if(actual!==8'((i+16)^((i+16)>>8)^8'ha5))",'if(actual!==expected424[i])')
(d/'fixture424-prg.hex').write_text(''.join('%02x\\n'%b for b in Path(ROM424_PATH).read_bytes()[16:272]),newline='\\n')
'''.replace('ROM424_PATH',repr(str(rom)))
s=once(s,anchor,anchor+extra)
sys.argv=['test_nes_nrom415_wiring.py','--build',str(a.build),'--fixture',str(a.fixture),'--out',str(a.out),'--run','--phase-ns','0']
exec(compile(s,str(ROOT/'tools/test_nes_nrom415_wiring.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom415_wiring.py')})
