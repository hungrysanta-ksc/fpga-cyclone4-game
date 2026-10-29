# SPDX-License-Identifier: MIT
"""Deterministic moving NROM bars; A holds red, release restores blue."""
import argparse,sys,json,hashlib
from pathlib import Path
from nes_delta231 import ROOT
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
s=(ROOT/'tools/build_nes_nrom428_visual.py').read_text()
def once(s,x,y):assert s.count(x)==1,(x[:50],s.count(x));return s.replace(x,y,1)
s=once(s,"label('fill');e(0x8d,0x07,0x20,0xe8);branch(0xd0,'fill');e(0x88);branch(0xd0,'fill')", """label('fill');e(0x8a,0x29,4);branch(0xf0,'empty');e(0xa9,1);jmp('tile')
label('empty');e(0xa9,0)
label('tile');e(0x8d,0x07,0x20,0xe8);branch(0xd0,'fill');e(0x88);branch(0xd0,'fill')
# Attributes are all palette0; initialize all palette RAM deterministically.
e(0xa9,0x23,0x8d,0x06,0x20,0xa9,0xc0,0x8d,0x06,0x20,0xa2,64,0xa9,0)
label('attr');e(0x8d,0x07,0x20,0xca);branch(0xd0,'attr')
e(0xa9,0x3f,0x8d,0x06,0x20,0xa9,0,0x8d,0x06,0x20,0xa2,32,0xa9,0x0f)
label('pal');e(0x8d,0x07,0x20,0xca);branch(0xd0,'pal')
e(0xa9,0,0x85,0)
""")
s=once(s,"0x8d,0x05,0x20,0x8d,0x05,0x20);jmp('frame')", "0xe6,0,0xa5,0,0x8d,0x05,0x20,0xa9,0,0x8d,0x05,0x20);jmp('frame')")
s=once(s,"d/'nrom16.nes'","d/'nrom471.nes'")
s=s.replace('controller A changes palette; no audio;', 'vertical bars scroll horizontally one pixel per NES frame; all attributes/palette initialized; A changes palette; no audio;')
# Use vblank NMI rather than STATUS polling so the scene itself does not miss updates.
s=once(s,"label('frame');e(0x2c,0x02,0x20);branch(0x10,'frame')", "label('frame');jmp('frame');label('nmi');e(0x48,0x2c,0x02,0x20)")
s=once(s,"0x8d,0x00,0x20,0xa9,0x1e", "0xa9,0x80,0x8d,0x00,0x20,0xa9,0x1e")
s=once(s,"0xa9,0,0x8d,0x05,0x20);jmp('frame')", "0xa9,0,0x8d,0x05,0x20);e(0x68,0x40)")
s=once(s,"prg[-6:]=bytes([0,0x80,0,0x80,0,0x80])", "prg[-6:]=bytes([labels['nmi']&255,labels['nmi']>>8,0,0x80,0,0x80])")
sys.argv=['build_nes_nrom428_visual.py','--out',str(a.out)]
exec(compile(s,str(ROOT/'tools/build_nes_nrom428_visual.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/build_nes_nrom428_visual.py')})
