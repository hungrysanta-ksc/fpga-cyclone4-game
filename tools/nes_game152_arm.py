# SPDX-License-Identifier: MIT
"""Preserve151 MCU control; strict62/DC and explicit tagged-context report."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out):
    e=baseline/'nes-game151/evidence'
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game151-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files']
    prior=json.loads((e/'arm/preparation151.json').read_bytes())
    assert not out.exists();out.mkdir(parents=True)
    copied={};changed={}
    for n in prior['copied']:
        src=e/'arm'/n;assert sha(src)==pins['arm/'+n]
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);copied[n]=sha(src)
    reps={
      'nes_h1_stm32.c':[('rx[1]!=0x61','rx[1]!=0x62',1)],
      'nes_rom_verify.c':[('rx[1]==0x61','rx[1]==0x62',1),('rx[1]!=0x61','rx[1]!=0x62',1)],
      'nes_run136.inc':[('candidate->board_id=0x61','candidate->board_id=0x62',1),('0xdb','0xdc',4)],
      'nes_menu_diagnostic.c':[('151','152',6),('board_expected_hex=61','board_expected_hex=62',1)],
      'nes_checkpoint112.c':[('151','152',2)],'VERSION':[('NES-GAME151-DEV','NES-GAME152-DEV',1)]}
    for n,changes in reps.items():
        p=out/'src'/n;s=p.read_text()
        for a,b,count in changes:assert s.count(a)==count,(n,a,s.count(a));s=s.replace(a,b)
        p.write_text(s,encoding='utf8',newline='\n');changed['src/'+n]=sha(p)
    (out/'preparation152.json').write_text(json.dumps(dict(copied=copied,changed=changed,added={},behavior_unchanged151=True,id=['62','DC']),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
