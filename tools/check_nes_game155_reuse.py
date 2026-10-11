# SPDX-License-Identifier: MIT
"""Prove that154 MCU recovery/observer behavior changes only identity/names."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','prepared','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game154/evidence';assert not a.out.exists();a.out.mkdir(parents=True)
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game154-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 prep=json.loads((a.arm/'preparation155.json').read_bytes());arm_pins={}
 for n,h in prep['copied'].items():
  assert sha(e/'arm'/n)==pins['arm/'+n]==h,n
  old=(e/'arm'/n).read_bytes();new=(a.arm/n).read_bytes()
  if n in prep['changed']:
   s=new.decode().replace('0x64','0x63').replace('0xde','0xdd').replace('board_expected_hex=64','board_expected_hex=63')
   if n.endswith(('nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION')):s=s.replace('155','154')
   assert s.replace('\r\n','\n')==old.decode().replace('\r\n','\n'),n
  else:assert new==old,n
  arm_pins[n]=sha(a.arm/n)
 for n in ['nes_run_observer134.sv','nes_screen_status151.sv','nes_rom_spi.sv']:
  assert sha(e/'asm'/n)==pins['asm/'+n]
  s=(a.prepared/n).read_text().replace("8'hde","8'hdd").replace("snapshot<={8'h64,","snapshot<={8'h63,")
  assert s==(e/'asm'/n).read_text(),n
 for n in ['nes_rom_service.sv','nes_rom_physical.sv','cart_nrom.sv','game-program.hex']:
  assert sha(a.prepared/n)==pins['asm/'+n],n
 for part in ['host','observer']:assert json.loads((e/part/'result.json').read_bytes())['passed']
 result=dict(passed=True,reused154_manifest=sha(e/'manifest.json'),arm_sources=arm_pins,changed_files=list(prep['changed']),reused154_host_and_observer_under_identity_normalization=True,new_host_run=False,new_observer_run=False,physical=False,scope='All MCU source bytes preserved or exactly identity/name normalized. Actual154 recovery/observer tests reused; new155 decoder and linked ARM checks are separate.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS155 recovery/observer behavior reused; identities normalized')
if __name__=='__main__':main()
