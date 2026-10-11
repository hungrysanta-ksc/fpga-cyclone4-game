# SPDX-License-Identifier: MIT
"""Package155 after collision/timing/ARM/identity checks; preserve target/restore."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,ROM_SHA,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','arm-check','asm','collision','reuse','decoder','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 e=a.baseline/'nes-game154/evidence';meta=json.loads((ROOT/'analysis/game154-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 old=e/'release/NES154-SMB3-PPU-STATE.zip';assert sha(old)==meta['package']['zip_sha256']
 arm=json.loads((a.arm_check/'result.json').read_bytes());asm=json.loads((a.asm/'result.json').read_bytes())
 collision=json.loads((a.collision/'result.json').read_bytes());reuse=json.loads((a.reuse/'result.json').read_bytes());decoder=json.loads((a.decoder/'result.json').read_bytes())
 assert all(x['passed'] for x in [collision,reuse,decoder,json.loads((a.asm/'timing150-phase.json').read_bytes())])
 assert arm['strong_nmi'] and arm['transport_source_matches']
 for n,h in collision['sources'].items():
  if n!='game155_collision_tb.sv':assert sha(a.asm/n)==h,n
 for n,h in reuse['arm_sources'].items():assert sha(a.arm/n)==h,n
 assert decoder['source_sha256']==sha(a.arm/'src/nes_run136.inc')
 for n,h in asm['inputs'].items():
  if n.endswith(('.sv','.v','.vhd','.sdc','.qsf')):assert sha(a.asm/n)==h,n
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n155.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
 for path in [a.arm/'preparation155.json',a.asm/'materialization155.json']:assert json.loads(path.read_bytes())['ids']==['64','DE']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(old) as z:
  manifest=json.loads(z.read('manifest.json'))
  for n,item in manifest['files'].items():
   data=z.read(n);assert digest(data)==item['sha256'] and len(data)==item['bytes'],n
   if n.startswith(('01-GAME154-SD-ROOT/','02-RESTORE044-SD-ROOT/')):
    dest=n.replace('154','155');blobs[dest]=data
    if not n.endswith(('firmware.stm','fpga_n154.bi3')) or n.startswith('02-'):preserved[dest]=digest(data)
 assert digest(blobs['01-GAME155-SD-ROOT/sd2snes/nes/game155.nes'])==ROM_SHA
 assert blobs['01-GAME155-SD-ROOT/NES GAME 155.nh1']==b''
 blobs['01-GAME155-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME155-SD-ROOT/sd2snes/fpga_n155.bi3']=fpga.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game155-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-GAME-155',ids=['64','DE'],physical=False,gameplay_passed=False,exact_hardware_cause_confirmed=False,
  ordinary_bg_prefetch=True,original_ppudata_overlap_retained=True,recovery154_reused=True,display_seconds_max=60,visible_hold_vblanks=30,
  audio=False,save_persistence=False,full_speed=False,screen_telemetry_trusted=False,rom_sha256=ROM_SHA,preserved=preserved,
  limitations=['Synthetic collision is not preceding hardware history','Held frames and DMA input gaps remain','External IO/MTBF incomplete'])
 blobs['decision155.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES155-SMB3-BG-PREFETCH',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/'NES155-SMB3-BG-PREFETCH.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','decision155.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),fpga_sha256=sha(fpga),normal_trial_ready=True,physical=False,gameplay_passed=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
