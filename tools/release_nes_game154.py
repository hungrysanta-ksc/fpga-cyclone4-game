# SPDX-License-Identifier: MIT
"""Package paired63/DD firmware and FPGA; preserve ROM/base/menu/restore bytes."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,ROM_SHA,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','arm-check','asm','host','decoder','observer','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 e=a.baseline/'nes-game153/evidence';meta=json.loads((ROOT/'analysis/game153-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 old=e/'release/NES153-SMB3-FAULT-RECOVERY.zip';assert sha(old)==meta['package']['zip_sha256']
 arm=json.loads((a.arm_check/'result.json').read_bytes());host=json.loads((a.host/'result.json').read_bytes())
 decoder=json.loads((a.decoder/'result.json').read_bytes());observer=json.loads((a.observer/'result.json').read_bytes())
 asm=json.loads((a.asm/'result.json').read_bytes());timing=json.loads((a.asm/'timing150-phase.json').read_bytes())
 assert arm['strong_nmi'] and arm['transport_source_matches'] and host['passed'] and decoder['passed'] and observer['passed'] and timing['passed']
 assert host['actual_sources']['nes_run136.inc']==decoder['source_sha256']==sha(a.arm/'src/nes_run136.inc')
 for n,h in host['actual_sources'].items():assert sha(a.arm/'src'/n)==h,n
 assert observer['observer_sha256']==sha(a.asm/'nes_run_observer134.sv')==asm['inputs']['nes_run_observer134.sv']
 for n,h in asm['inputs'].items():
  # ASM adds generated files, but must not mutate the selected input tree.
  if n.endswith(('.sv','.v','.vhd','.sdc','.qsf')):assert sha(a.asm/n)==h,n
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n154.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
 assert json.loads((a.arm/'preparation154.json').read_bytes())['ids']==['63','DD']
 assert json.loads((a.asm/'materialization154.json').read_bytes())['ids']==['63','DD']
 blobs={};digest=lambda b:hashlib.sha256(b).hexdigest()
 with zipfile.ZipFile(old) as z:
  m=json.loads(z.read('manifest.json'))
  for n,item in m['files'].items():
   data=z.read(n);assert digest(data)==item['sha256'] and len(data)==item['bytes'],n
   if n.startswith(('01-GAME153-SD-ROOT/','02-RESTORE044-SD-ROOT/')):blobs[n.replace('153','154')]=data
 assert digest(blobs['01-GAME154-SD-ROOT/sd2snes/nes/game154.nes'])==ROM_SHA
 assert blobs['01-GAME154-SD-ROOT/NES GAME 154.nh1']==b''
 blobs['01-GAME154-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 blobs['01-GAME154-SD-ROOT/sd2snes/fpga_n154.bi3']=fpga.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game154-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-GAME-154',ids=['63','DD'],physical=False,ppu_deadline_fixed=False,
  supplemental_state_bits=64,read_after_stop=True,malformed_auxiliary_reply_preserves_recovery=True,
  transport_clock_guards_retained=True,display_seconds_max=60,visible_hold_vblanks=30,
  audio=False,save_persistence=False,full_speed=False,screen_telemetry_trusted=False,
  prior153_manifest_sha256=meta['manifest_sha256'],rom_sha256=ROM_SHA,
  changed='First-fault PPU state and paired identity only; ROM service/core decisions unchanged.',
  limitations=['Actual153 PPU deadline cause unresolved','Synthetic observer/host data is not a hardware observation',
   'Input DMA/wait gaps and held-frame presentation remain','Full external IO/MTBF signoff remains open'])
 blobs['decision154.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES154-SMB3-PPU-STATE',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 a.out.mkdir(parents=True);archive=a.out/'NES154-SMB3-PPU-STATE.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n in ['START-HERE.ko.md','decision154.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),
  fpga_sha256=sha(fpga),normal_trial_ready=True,physical=False,ppu_deadline_fixed=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
