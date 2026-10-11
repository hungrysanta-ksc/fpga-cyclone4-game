# SPDX-License-Identifier: MIT
"""Exact158 reuse except read eligibility and strict159 identities."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_game159 import OLD,NEW
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','arm','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game158/evidence';o=a.prepared
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game158-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prep=json.loads((o/'materialization159.json').read_bytes())
 unchanged={};normalized={}
 for n in prep['copied']:
  old=e/'asm'/n;assert sha(old)==pins['asm/'+n]
  if n not in prep['changed']:assert sha(o/n)==sha(old);unchanged[n]=sha(o/n)
  else:
   s=(o/n).read_text();ref=old.read_text()
   if n=='rtl/nes.v':assert s==ref.replace(OLD,NEW)
   else:
    assert s==ref.replace("8'he1","8'he2").replace("snapshot<={8'h67,","snapshot<={8'h68,"),n
    normalized[n]='identity only; exact158 behavior'
 assert set(prep['changed'])=={'rtl/nes.v','nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','nes_pad_trace156.sv','nes_ppu_history157.sv'}
 ap=json.loads((a.arm/'preparation159.json').read_bytes())
 for n,h in ap['copied'].items():
  assert sha(e/'arm'/n)==pins['arm/'+n]
  s=(a.arm/n).read_bytes();old=(e/'arm'/n).read_bytes()
  if n in ap['changed']:
   old=old.replace(b'0xe1',b'0xe2').replace(b'rx[1]!=0x67',b'rx[1]!=0x68').replace(b'rx[1]==0x67',b'rx[1]==0x68').replace(b'candidate->board_id=0x67',b'candidate->board_id=0x68').replace(b'board_expected_hex=67',b'board_expected_hex=68')
   if n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:old=old.replace(b'158',b'159')
   assert s.replace(b'\r\n',b'\n')==old.replace(b'\r\n',b'\n'),n
  else:assert s==old,n
 assert '.CS             (apu_cs && (cpu_rnw' in (o/'rtl/nes.v').read_text()
 a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=True,normalized=normalized,unchanged=unchanged,apu_isolation_retained=True,mapper_service_reader_ppu_unchanged=True,arm_identity_only=True,physical=False,scope='One early-read qualification equation plus identity-only control paths. Source equality, not gate equivalence or actual game proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS159 one-equation/control-path reuse')
if __name__=='__main__':main()
