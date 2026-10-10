# SPDX-License-Identifier: MIT
"""Verify frozen146 evidence and source pins without rerunning finished builds."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/screen146-verification.json').read_bytes());e=a.baseline/'nes-display146/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for name in ['normal','mixed','late','bad_length','bad_header','negative','bus']:
  v=json.loads((e/name/'result.json').read_bytes());assert v['passed'],name
  if name in ['normal','mixed','late']:
   assert v['model']==[30,60240,0] and v['exact_rgb_frames']==395
   assert [x['hold_frames'] for x in v['timing']]==[30]*12+[2]*18
 assert len(json.loads((e/'host/result.json').read_bytes())['cases'])==21
 arm=json.loads((e/'armcheck/result.json').read_bytes());assert arm['strong_nmi'] and arm['host_sources_match']
 assert sha(e/'arm/src/obj-nes-100/firmware.stm')==m['package']['firmware_sha256']
 old=a.baseline/'nes-hold145/evidence'
 for n,h in m['unchanged_routing_inputs'].items():assert sha(e/'fit'/n)==sha(old/'fit'/n)==h,n
 assert sha(e/'arm/src/nes_rom_spi.c')==sha(old/'arm/src/nes_rom_spi.c')
 assert sha(e/'host/fixture.nes')==m['package']['fixture_sha256']
 z=e/'release/NES146-SCREEN-and-RESTORE044.zip';assert sha(z)==m['package']['zip_sha256']
 with zipfile.ZipFile(z) as archive:
  manifest=json.loads(archive.read('manifest.json'));assert len(archive.namelist())==13
  for n,v in manifest['files'].items():
   data=archive.read(n);assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['sha256'],n
 print('PASS146 frozen evidence/public sources/reused routing/package; physical146 pending')
if __name__=='__main__':main()
