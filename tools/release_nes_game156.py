# SPDX-License-Identifier: MIT
"""Package one sound-isolation trial; require changed-boundary and fit evidence."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,ROM_SHA,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','arm-check','asm','test','host','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 e=a.baseline/'nes-game155/evidence';m=json.loads((ROOT/'analysis/game155-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 old=e/'release/NES155-SMB3-BG-PREFETCH.zip';assert sha(old)==m['package']['zip_sha256']
 arm=json.loads((a.arm_check/'result.json').read_bytes());asm=json.loads((a.asm/'result.json').read_bytes())
 test=json.loads((a.test/'result.json').read_bytes());host=json.loads((a.host/'result.json').read_bytes())
 timing=json.loads((a.asm/'timing150-phase.json').read_bytes())
 assert test['passed'] and host['passed'] and timing['passed']
 assert timing['nominal_sdc_sha256']==sha(e/'asm/board.sdc') and timing['new_fit'] is False
 assert arm['strong_nmi'] and arm['transport_source_matches']
 for n,h in test['sources'].items():assert sha(a.asm/n)==h,n
 assert host['source_sha256']==sha(a.arm/'src/nes_run136.inc')
 assert host['format_source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 for root,prep in [(a.arm,'preparation156.json'),(a.asm,'materialization156.json')]:
  data=json.loads((root/prep).read_bytes());assert data['ids']==['65','DF']
  for n,h in data['copied'].items():assert sha(root/n)==data['changed'].get(n,h),n
  for n,h in data['added'].items():assert sha(root/n)==h,n
 preserved_rtl={}
 for n in ['rtl/ppu.sv','rtl/apu.sv','cart_nrom.sv','nes_probe.sv','nes_rom_service.sv','nes_rom_physical.sv','nes_rom_loader.sv','nes_game_frame150.sv','nes_game_bus151.sv','game-program.hex']:
  assert sha(a.asm/n)==sha(e/'asm'/n);preserved_rtl[n]=sha(a.asm/n)
 assert (a.asm/'board.sdc').read_text()==(e/'asm/board.sdc').read_text()+'\n'+(ROOT/'src/nes/diagnostics/nes_game156_budget.sdc').read_text()
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n156.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(old) as z:
  for n,item in json.loads(z.read('manifest.json'))['files'].items():
   data=z.read(n);assert digest(data)==item['sha256'] and len(data)==item['bytes']
   if n.startswith(('01-GAME155-SD-ROOT/','02-RESTORE044-SD-ROOT/')):
    dest=n.replace('155','156');blobs[dest]=data
    if not n.endswith(('firmware.stm','fpga_n155.bi3')) or n.startswith('02-'):preserved[dest]=digest(data)
 assert digest(blobs['01-GAME156-SD-ROOT/sd2snes/nes/game156.nes'])==ROM_SHA
 assert blobs['01-GAME156-SD-ROOT/NES GAME 156.nh1']==b''
 blobs['01-GAME156-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME156-SD-ROOT/sd2snes/fpga_n156.bi3']=fpga.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game156-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-GAME-156',ids=['65','DF'],physical=False,gameplay_passed=False,exact_hardware_cause_confirmed=False,
  apu_channel_writes_blocked=True,apu_frame_counter_writes_retained=True,rom_sha256=ROM_SHA,preserved=preserved,preserved_rtl=preserved_rtl,
  pad_trace='Last16 changed completed8bit reads; NES master cycles rounded down to256; frozen after fault/STOP; no SD during RUN',
  limitations=['Isolation changes APU status/DMC and possibly game control flow','Sound driver CPU activity is not removed','Not full speed/audio/save/IO-MTBF proof'])
 blobs['decision156.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES156-SMB3-SOUND-PAD',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/'NES156-SMB3-SOUND-PAD.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','decision156.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),fpga_sha256=sha(fpga),normal_trial_ready=True,physical=False,gameplay_passed=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
