# SPDX-License-Identifier: MIT
"""Pin all unchanged160 sources, exact service edits and six-vblank client."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_game161 import patch161
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','arm','client','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game160/evidence';o=a.prepared
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game160-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prep=json.loads((o/'materialization161.json').read_bytes())
 expected={n:(e/'asm'/n).read_text() for n in prep['copied']}
 def edit(n,before,after,c=1):assert expected[n].count(before)==c;expected[n]=expected[n].replace(before,after)
 patch161(edit)
 for n in ['nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','nes_pad_trace156.sv','nes_ppu_history157.sv']:
  expected[n]=expected[n].replace("8'he3","8'he4").replace("snapshot<={8'h69,","snapshot<={8'h6a,")
 expected['game-program.hex']=(a.client/'client/game-program.hex').read_text()
 old=(ROOT/'tools/build_nes_game152.py').read_text();new=(ROOT/'tools/build_nes_game161.py').read_text()
 assert new==old.replace('152','161').replace('for30 vblanks','for6 vblanks').replace('0xa2,30,0','0xa2,6,0').replace('Single frozen frame; full-frame forced-blank DMA, not 60fps presentation.','Six-vblank visible hold; unchanged full-frame forced-blank DMA. Reduced snapshot age, not60fps or flicker-free presentation.')
 unchanged={};changed={}
 for n in prep['copied']:
  assert sha(e/'asm'/n)==pins['asm/'+n] and (o/n).read_text()==expected[n],n
  (unchanged if sha(o/n)==sha(e/'asm'/n) else changed)[n]=sha(o/n)
 assert set(changed)=={'nes_rom_service.sv','game-program.hex','nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','nes_pad_trace156.sv','nes_ppu_history157.sv'}
 for n in ['cart_nrom.sv','nes_rom_physical.sv','rtl/ppu.sv','rtl/nes.v','board.sdc']:assert n in unchanged
 ap=json.loads((a.arm/'preparation161.json').read_bytes())
 for n in ap['copied']:
  assert sha(e/'arm'/n)==pins['arm/'+n]
  old=(e/'arm'/n).read_bytes();s=(a.arm/n).read_bytes()
  if n in ap['changed']:
   old=old.replace(b'0xe3',b'0xe4').replace(b'rx[1]!=0x69',b'rx[1]!=0x6a').replace(b'rx[1]==0x69',b'rx[1]==0x6a').replace(b'candidate->board_id=0x69',b'candidate->board_id=0x6a').replace(b'board_expected_hex=69',b'board_expected_hex=6A')
   if n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:old=old.replace(b'160',b'161')
   assert s.replace(b'\r\n',b'\n')==old.replace(b'\r\n',b'\n'),n
  else:assert s==old,n
 a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=True,changed=changed,unchanged=unchanged,client152_only_hold_and_identity=True,raw_read159_restart160_retained=True,mapper_ppu_reader_clocks_unchanged=True,apu_isolation_retained=True,arm_identity_only=True,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS161 service/hold6/IDs only; other160 sources preserved')
if __name__=='__main__':main()
