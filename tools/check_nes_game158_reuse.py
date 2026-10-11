# SPDX-License-Identifier: MIT
"""Audit the two functional changes and exact identity-only control-path reuse."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_game158 import patch_mapper
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','arm','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game157/evidence';o=a.prepared
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game157-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prep=json.loads((o/'materialization158.json').read_bytes())
 unchanged={};normalized={}
 for n in prep['copied']:
  old=e/'asm'/n;assert sha(old)==pins['asm/'+n]
  if n not in prep['changed']:assert sha(o/n)==sha(old);unchanged[n]=sha(o/n)
  else:
   s=(o/n).read_text();ref=old.read_text()
   if n=='cart_nrom.sv':assert s==patch_mapper(ref)
   elif n=='rtl/nes.v':assert s==ref.replace('cart_top multi_mapper (','cart_top multi_mapper (.game158_preview_write(mw_int && !reset_noSS),')
   else:
    assert s==ref.replace("8'he0","8'he1").replace("snapshot<={8'h66,","snapshot<={8'h67,"),n
    normalized[n]='identity only; exact157 behavior'
 assert set(prep['changed'])=={'cart_nrom.sv','rtl/nes.v','nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','nes_pad_trace156.sv','nes_ppu_history157.sv'}
 ap=json.loads((a.arm/'preparation158.json').read_bytes())
 for n,h in ap['copied'].items():
  assert sha(e/'arm'/n)==pins['arm/'+n]
  s=(a.arm/n).read_bytes();old=(e/'arm'/n).read_bytes()
  if n in ap['changed']:
   old=old.replace(b'0xe0',b'0xe1').replace(b'rx[1]!=0x66',b'rx[1]!=0x67').replace(b'rx[1]==0x66',b'rx[1]==0x67').replace(b'candidate->board_id=0x66',b'candidate->board_id=0x67').replace(b'board_expected_hex=66',b'board_expected_hex=67')
   if n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:old=old.replace(b'157',b'158')
   # Materializer normalizes line endings for changed text only.
   assert s.replace(b'\r\n',b'\n')==old.replace(b'\r\n',b'\n'),n
  else:assert s==old,n
 assert '.CS             (apu_cs && (cpu_rnw' in (o/'rtl/nes.v').read_text()
 a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=True,normalized=normalized,unchanged=unchanged,apu_isolation_retained=True,service_reader_ppu_unchanged=True,mapper_state_commit_unchanged=True,arm_identity_only=True,physical=False,scope='Source equality for unchanged logic, pure pending-write hint lookup and one raw-write connection; not gate equivalence or game-level proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS158 scope/control-path reuse')
if __name__=='__main__':main()
