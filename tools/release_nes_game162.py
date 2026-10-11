# SPDX-License-Identifier: MIT
"""Package audio162 from checked artifacts, preserving161 ROM/base/menu/restore."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,ROM_SHA,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','asm','arm','arm-check','audio','regression','host','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 e=a.baseline/'nes-game161/evidence';old=json.loads((ROOT/'analysis/game161-verification.json').read_bytes())
 assert sha(e/'manifest.json')==old['manifest_sha256']
 old_zip=e/'release/NES161-SMB3-CACHE-HOLD6.zip';assert sha(old_zip)==old['package']['zip_sha256']
 for root in [a.audio,a.regression,a.host]:assert json.loads((root/'result.json').read_bytes())['passed']
 arm=json.loads((a.arm_check/'result.json').read_bytes());assembled=json.loads((a.asm/'result.json').read_bytes())
 assert arm['strong_nmi'] and arm['transport_source_matches']
 for f in ['timing150-phase.json','audio162-timing.json']:assert json.loads((a.asm/f).read_bytes())['passed']
 for root,prep in [(a.asm,'materialization162.json'),(a.arm,'preparation162.json')]:
  m=json.loads((root/prep).read_bytes());assert m['ids']==['6B','E5']
  for n,h in m['copied'].items():assert sha(root/n)==m['changed'].get(n,h),n
  for n,h in m['added'].items():assert sha(root/n)==h,n
 for n,h in json.loads((a.audio/'result.json').read_bytes())['sources'].items():
  assert sha(ROOT/'src/fpga/gbc_dac_psram.sv' if n=='gbc_reference' else a.asm/n)==h,n
 reg=json.loads((a.regression/'result.json').read_bytes())
 for n,h in reg['sources'].items():assert sha((a.regression if n.startswith('game') else a.asm)/n)==h,n
 # Unchanged frame/DMA/hold/pad/service boundary evidence is reused by exact bytes.
 reused={}
 for n in ['game-program.hex','nes_game_frame150.sv','nes_game_bus151.sv','nes_game_pad150.sv','nes_rom_service.sv','nes_rom_physical.sv','nes_live_joint.sv','nes_probe.sv','rtl/ppu.sv','cart_nrom.sv','board.sdc']:
  assert (a.asm/n).read_bytes()==(e/'asm'/n).read_bytes(),n;reused[n]=sha(a.asm/n)
 original=(e/'asm/rtl/nes.v').read_text();new=(a.asm/'rtl/nes.v').read_text()
 assert new.replace('.CS             (apu_cs), //162 restore all APU writes, including DMC',".CS             (apu_cs && (cpu_rnw || addr[4:0]==5'h17)), //156 channel-write isolation; frame counter/read path retained")==original
 host=json.loads((a.host/'result.json').read_bytes());assert host['source_sha256']==sha(a.arm/'src/nes_run136.inc') and host['format_source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n162.bi3';assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==assembled['packed_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(old_zip) as z:
  for n,v in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert digest(b)==v['sha256'] and len(b)==v['bytes']
   if n.startswith(('01-GAME161-SD-ROOT/','02-RESTORE044-SD-ROOT/')):
    dst=n.replace('161','162');blobs[dst]=b
    if n.startswith('02-') or not n.endswith(('firmware.stm','fpga_n161.bi3')):preserved[dst]=digest(b)
 assert digest(blobs['01-GAME162-SD-ROOT/sd2snes/nes/game162.nes'])==ROM_SHA
 blobs['01-GAME162-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME162-SD-ROOT/sd2snes/fpga_n162.bi3']=fpga.read_bytes()
 assert blobs['01-GAME162-SD-ROOT/NES GAME 162.nh1']==b''
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game162-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-GAME-162',ids=['6B','E5'],physical_audio=False,normal_trial_ready=True,continuous_video=False,held_input_fixed=False,run_budget_seconds=60,reset_logging=False,apu_writes_blocked=False,reused161_sources=reused,preserved=preserved,limits=['First sound output trial, not analog-quality or full-game approval','Same161 snapshot video and pad path; continuous video is next priority','No audio/video latency compensation yet','DMC modeled byte response in focused test; actual ROM contention still needs game test','MTBF/full IO/PCB/reset recovery limits remain open'])
 blobs['decision162.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES162-SMB3-AUDIO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()});blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 a.out.mkdir(parents=True);archive=a.out/'NES162-SMB3-AUDIO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','decision162.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),fpga_sha256=sha(fpga),normal_trial_ready=True,physical_audio=False,reused161_sources=reused)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
