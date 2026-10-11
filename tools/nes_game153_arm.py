# SPDX-License-Identifier: MIT
"""Accept the released152 PPU context tag; retain every other reply guard."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out):
    e=baseline/'nes-game152/evidence'
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game152-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files']
    prior=json.loads((e/'arm/preparation152.json').read_bytes())
    assert not out.exists();out.mkdir(parents=True)
    copied={};changed={}
    for n in prior['copied']:
        src=e/'arm'/n;assert sha(src)==pins['arm/'+n]
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);copied[n]=sha(src)
    replacements={
      'nes_run136.inc':[('(hi[3]&0x80u) || ', '',1),
        (' if(hi[1]!=0xdc', ' /* Bit63 is the152 PPU address tag, not a reserved/invalid bit.\n'
         '  * Keep both IDs, valid flags, sticky error and format revision strict. */\n if(hi[1]!=0xdc',1)],
      'nes_menu_diagnostic.c':[('152','153',7)],
      'nes_checkpoint112.c':[('152','153',2)],
      'VERSION':[('NES-GAME152-DEV','NES-GAME153-DEV',1)]}
    for n,changes in replacements.items():
        p=out/'src'/n;s=p.read_text(encoding='utf8')
        for before,after,count in changes:
            assert s.count(before)==count,(n,before,s.count(before));s=s.replace(before,after)
        p.write_text(s,encoding='utf8',newline='\n');changed['src/'+n]=sha(p)
    assert len(changed)==4
    (out/'preparation153.json').write_text(json.dumps(dict(copied=copied,changed=changed,added={},
        ids=['62','DC'],fpga_reused152=True,ppu_deadline_fixed=False),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
