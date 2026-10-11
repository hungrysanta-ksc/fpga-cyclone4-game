# SPDX-License-Identifier: MIT
"""Check160 preview-only changes against frozen159; no gate equivalence claim."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_game160 import patch160
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','arm','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game159/evidence';o=a.prepared
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game159-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prep=json.loads((o/'materialization160.json').read_bytes())
 expected={n:(e/'asm'/n).read_text() for n in prep['copied']}
 def edit(n,before,after,c=1):assert expected[n].count(before)==c,(n,before);expected[n]=expected[n].replace(before,after)
 patch160(edit)
 for n in ['nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','nes_pad_trace156.sv','nes_ppu_history157.sv']:
  expected[n]=expected[n].replace("8'he2","8'he3").replace("snapshot<={8'h68,","snapshot<={8'h69,")
 unchanged={};changed={}
 for n in prep['copied']:
  assert sha(e/'asm'/n)==pins['asm/'+n]
  assert (o/n).read_text()==expected[n],n
  if sha(o/n)==sha(e/'asm'/n):unchanged[n]=sha(o/n)
  else:changed[n]=sha(o/n)
 assert set(changed)=={'board.sdc','rtl/ppu.sv','rtl/nes.v','nes_probe.sv','nes_live_joint.sv','nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','nes_pad_trace156.sv','nes_ppu_history157.sv'}
 for n in ['cart_nrom.sv','nes_rom_service.sv','nes_rom_physical.sv']:assert n in unchanged
 assert 'assign rom_cpu_address_valid=mr_int && prg_addr[15] && prg_allow;' in expected['rtl/nes.v']
 ap=json.loads((a.arm/'preparation160.json').read_bytes())
 for n in ap['copied']:
  assert sha(e/'arm'/n)==pins['arm/'+n]
  old=(e/'arm'/n).read_bytes();s=(a.arm/n).read_bytes()
  if n in ap['changed']:
   old=old.replace(b'0xe2',b'0xe3').replace(b'rx[1]!=0x68',b'rx[1]!=0x69').replace(b'rx[1]==0x68',b'rx[1]==0x69').replace(b'candidate->board_id=0x68',b'candidate->board_id=0x69').replace(b'board_expected_hex=68',b'board_expected_hex=69')
   if n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:old=old.replace(b'159',b'160')
   assert s.replace(b'\r\n',b'\n')==old.replace(b'\r\n',b'\n'),n
  else:assert s==old,n
 a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=True,changed=changed,unchanged=unchanged,raw_read159_retained=True,mapper_service_reader_unchanged=True,apu_isolation_retained=True,arm_identity_only=True,physical=False,scope='Rendering-restart hint and wiring only; functional PPU register/latch/address/read behavior unchanged. Exact source comparison, not gate equivalence.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS160 preview/wiring and159 reuse')
if __name__=='__main__':main()
