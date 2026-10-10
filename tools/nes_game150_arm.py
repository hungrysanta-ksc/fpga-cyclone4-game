# SPDX-License-Identifier: MIT
"""Reuse149 MCU behavior; bind strict150 names and60/DA identities."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out):
    assert not out.exists();e=baseline/'nes-game149/evidence'
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game149-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={};changes={}
    for n,h in pins.items():
        if not n.startswith('arm/'):continue
        rel=n[4:];p=Path(rel)
        if any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']:continue
        assert sha(e/n)==h,n
        dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,dest);copied[rel]=h
    replacements={
      'nes_h1_stm32.c':[('rx[1]!=0x5f','rx[1]!=0x60',1)],
      'nes_rom_verify.c':[('0x5f','0x60',2)],
      'nes_run136.inc':[('0x5f','0x60',1),('0xd9','0xda',4)],
      'nes_menu_diagnostic.c':[('149','150',6),('board_expected_hex=5f','board_expected_hex=60',1)],
      'nes_checkpoint112.c':[('149','150',2)],
      'VERSION':[('NES-GAME149-DEV','NES-GAME150-DEV',1)]}
    for n,reps in replacements.items():
        p=out/'src'/n;s=p.read_text(encoding='utf8');original=s
        for before,after,count in reps:
            assert s.count(before)==count,(n,before,s.count(before),count);s=s.replace(before,after)
        # Only the listed, count-checked identity/name substitutions are made.
        # Do not reverse globally: command0x60 already exists in149.
        p.write_text(s,encoding='utf8',newline='\n');changes['src/'+n]=sha(p)
    result=dict(copied=copied,changed=changes,added={},candidate='NES-GAME-150',
      board_id=0x60,observer_id=0xda,behavior_unchanged149=True,physical=False)
    (out/'preparation150.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
