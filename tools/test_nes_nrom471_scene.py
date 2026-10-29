# SPDX-License-Identifier: MIT
import argparse,sys,json
from pathlib import Path
from nes_delta231 import ROOT
p=argparse.ArgumentParser();p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
s=(ROOT/'tools/test_nes_nrom424_visual.py').read_text()
s=s.replace('inputs.a=emu.getState().frameCount>=80','inputs.a=emu.getState().frameCount>=80 and emu.getState().frameCount<120').replace('n>=80 and 0x41 or 0x40','n>=80 and n<120 and 0x41 or 0x40').replace('n==60 or n==100','n==60 or n==61 or n==100 or n==140').replace('if n==105 then','if n==145 then')
s=s.replace("out:write(string.format('%d\\t%d\\t%d\\t%d\\t%d\\n'", "local hash=0;for i=1,#buf do hash=((hash<<5)-hash+buf[i])&0xffffffff end\n  out:write(string.format('%d\\t%d\\t%d\\t%d\\t%d\\n'")
s=s.replace('count,buf[80*256+81]','count,hash')
s=s[:s.index('assert len(rows)==2')]+'''assert len(rows)==4 and [r[0] for r in rows]==[60,61,100,140],rows
assert [r[1] for r in rows]==[0x21,0x21,0x16,0x21],rows
assert all(r[3]>=2 for r in rows) and rows[0][4]!=rows[1][4],rows
res={'passed':True,'rom_sha256':sha(a.rom),'frames':rows,'scope':'Mesen NES moving pixels with A hold/release palette behavior; injected bit, not physical SNES'}
(d/'result.json').write_text(json.dumps(res,indent=2)+'\\n');print(json.dumps(res))
'''
sys.argv=['test_nes_nrom424_visual.py','--rom',str(a.rom),'--out',str(a.out)]
exec(compile(s,str(ROOT/'tools/test_nes_nrom424_visual.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom424_visual.py')})

r=json.loads((a.out/'result.json').read_text(encoding='utf8'));scroll=[]
for n in [60,61,100,140]:
 values=dict(x.split('=',1) for x in (a.out/f'state-{n}.txt').read_text(encoding='utf8').splitlines() if '=' in x)
 scroll.append((int(values['ppu.tmpVideoRamAddr'])&31)*8+int(values['ppu.xScroll']))
assert [(x-scroll[0])%256 for x in scroll]==[0,1,40,80],scroll
r['NMI_scroll_x_samples']=scroll;r['one_pixel_each_NES_frame_verified']=True
(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
