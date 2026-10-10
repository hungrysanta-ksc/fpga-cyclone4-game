# SPDX-License-Identifier: MIT
"""Verify private145 evidence and public pins; a public clone alone is insufficient."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/screen145-verification.json').read_bytes());e=a.baseline/'nes-hold145/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for case in ['normal','mixed','bad_length','bad_header']:
  c=json.loads((e/case/'result.json').read_bytes());assert c['passed']
  if case in ['normal','mixed']:
   assert c['held_rgb_samples']==9 and c['black_rgb_samples']==3
   assert c['no_ppu_dma_or_packet_write_during_hold']
   for t in c['timing']:assert t['black_tv_frames']>=90 and t['held_tv_frames']>=180
 assert len(json.loads((e/'host/result.json').read_bytes())['cases'])==21
 arm=json.loads((e/'armcheck/result.json').read_bytes());assert arm['strong_nmi'] and arm['host_sources_match']
 assert sha(e/'arm/src/obj-nes-100/firmware.stm')==m['package']['firmware_sha256']
 old=a.baseline/'nes-pattern144/evidence-final'
 for n,h in m['unchanged_routing_inputs'].items():assert sha(e/'fit'/n)==sha(old/'fit'/n)==h,n
 assert sha(e/'arm/src/nes_rom_spi.c')==sha(old/'arm/src/nes_rom_spi.c')
 assert sha(e/'host/fixture.nes')==m['package']['fixture_sha256']==sha(old/'fixture/screen144.nes')
 z=e/'release/NES145-SCREEN-and-RESTORE044.zip';assert sha(z)==m['package']['zip_sha256']
 with zipfile.ZipFile(z) as archive:
  manifest=json.loads(archive.read('manifest.json'))
  assert len(archive.namelist())==13
  for n,v in manifest['files'].items():
   data=archive.read(n);assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['sha256'],n
 print('PASS145 frozen evidence/public pins/package; physical result pending')
if __name__=='__main__':main()
