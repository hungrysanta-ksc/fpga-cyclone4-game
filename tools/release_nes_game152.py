# SPDX-License-Identifier: MIT
"""Package actual SMB3 input/context trial; explicitly not a PPU deadline fix."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,ROM_SHA,sha
from nes_cf68_pair_preflight import decode

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','arm-check','asm','test','client','old-client','rom','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and sha(a.rom)==ROM_SHA
 arm=json.loads((a.arm_check/'result.json').read_bytes());asm=json.loads((a.asm/'result.json').read_bytes())
 test=json.loads((a.test/'result.json').read_bytes());client=json.loads((a.client/'result.json').read_bytes())
 pad=json.loads((a.client/'input-result.json').read_bytes());oldpad=json.loads((a.old_client/'input-result.json').read_bytes())
 timing=json.loads((a.asm/'timing150-phase.json').read_bytes())
 assert arm['strong_nmi'] and arm['transport_source_matches'] and test['passed'] and client['passed'] and timing['passed']
 assert pad['passed'] and pad['polls']==62 and len(pad['short_pulses'])==8
 assert oldpad['passed'] and oldpad['old_control'] and oldpad['polls']==2 and not oldpad['short_pulses']
 assert test['service_behavior_exact151'] and not test['ppu_error_fixed']
 assert sha(a.asm/'nes_rom_service.sv')==sha(a.test/'nes_rom_service.sv')==sha(ROOT/'src/nes/diagnostic/nes_rom_service152.sv')
 assert sha(a.asm/'game-program.hex')==sha(a.client/'client/game-program.hex')==sha(a.test/'game-program.hex')
 e=a.baseline/'nes-game151/evidence';m=json.loads((ROOT/'analysis/game151-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 material=json.loads((a.asm/'materialization152.json').read_bytes())
 for n,h in material['inputs151'].items():
  assert sha(e/'asm'/n)==h==pins['asm/'+n]
  if n not in material['changed']:assert sha(a.asm/n)==h,n
 assert json.loads((e/'test/result.json').read_bytes())['passed']
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n152.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
 assert decode(fpga.read_bytes())==(a.asm/'output_files/board.rbf').read_bytes()
 old=a.baseline/'nes-run136/evidence/release01/NES136-MINIMUM-RUN-and-RESTORE044.zip'
 assert sha(old)==json.loads((ROOT/'analysis/run136-verification.json').read_bytes())['package']['zip_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={}
 with zipfile.ZipFile(old) as z:
  manifest=json.loads(z.read('manifest.json'))
  for n in ['01-RUN136-SD-ROOT/sd2snes/fpga_base.bi3','01-RUN136-SD-ROOT/sd2snes/m3nu.bin',
            '02-RESTORE044-SD-ROOT/sd2snes/firmware.stm','02-RESTORE044-SD-ROOT/sd2snes/fpga_base.bi3','02-RESTORE044-SD-ROOT/sd2snes/m3nu.bin']:
   b=z.read(n);assert digest(b)==manifest['files'][n]['sha256'];blobs[n.replace('01-RUN136','01-GAME152')]=b
 blobs.update({'01-GAME152-SD-ROOT/sd2snes/firmware.stm':fw.read_bytes(),
   '01-GAME152-SD-ROOT/sd2snes/fpga_n152.bi3':fpga.read_bytes(),
   '01-GAME152-SD-ROOT/sd2snes/nes/game152.nes':a.rom.read_bytes(),'01-GAME152-SD-ROOT/NES GAME 152.nh1':b'',
   'START-HERE.ko.md':(ROOT/'docs/nes-game152-instructions.ko.md').read_bytes()})
 decision=dict(candidate='NES-GAME-152',board='62',observer='DC',target_rom_sha256=ROM_SHA,
   normal_trial_ready=True,physical=False,display_seconds=60,ppu_error_fixed=False,
   context_format='bit63=1: low25=zeroextended actual PPU demand; bit63=0: CPU physical. Pending remains bits46:25. Type tag is not error cause.',
   visible_hold_vblanks=30,pad_poll='each held vblank; DMA/wait gaps remain',full_speed=False,input=True,audio=False,
   emphasis=False,save_persistence=False,unchanged044_retest=False,timing=timing,screen_telemetry_trusted=False)
 blobs['decision152.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES152-SMB3-INPUT-CONTEXT',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 a.out.mkdir(parents=True);archive=a.out/'NES152-SMB3-INPUT-CONTEXT.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n in ['START-HERE.ko.md','decision152.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),
   fpga_sha256=sha(fpga),rom_sha256=ROM_SHA,normal_trial_ready=True,physical=False,ppu_error_fixed=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
