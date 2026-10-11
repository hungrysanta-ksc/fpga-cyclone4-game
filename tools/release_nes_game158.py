# SPDX-License-Identifier: MIT
"""Package pending MMC3 write prediction158 with verified binaries and unchanged game/restore."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,ROM_SHA,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','arm-check','asm','test','host','reuse','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 e=a.baseline/'nes-game157/evidence';m=json.loads((ROOT/'analysis/game157-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 old=e/'release/NES157-SMB3-PPU-HISTORY.zip';assert sha(old)==m['package']['zip_sha256']
 arm=json.loads((a.arm_check/'result.json').read_bytes());asm=json.loads((a.asm/'result.json').read_bytes())
 test=json.loads((a.test/'result.json').read_bytes());host=json.loads((a.host/'result.json').read_bytes());reuse=json.loads((a.reuse/'result.json').read_bytes())
 timing=json.loads((a.asm/'timing150-phase.json').read_bytes())
 assert test['passed'] and host['passed'] and reuse['passed'] and timing['passed']
 assert timing['nominal_sdc_sha256']==m['timing']['nominal_sdc_sha256'] and timing['new_fit'] is False
 assert arm['strong_nmi'] and arm['transport_source_matches']
 for n,h in test['sources'].items():
  src=a.test/n if n.startswith('game158_') else a.asm/n
  assert sha(src)==h,n
 assert sha(a.test/'game158_mapper_tb.sv')==sha(ROOT/'tests/nes-functional/game158_mapper_tb.sv')
 assert 'PASS158 mapper lookup 536 commits' in (a.test/'mapper.log').read_text()
 for n,h in reuse['unchanged'].items():assert sha(a.asm/n)==h,n
 assert host['source_sha256']==sha(a.arm/'src/nes_run136.inc')
 assert host['format_source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 for root,prep in [(a.arm,'preparation158.json'),(a.asm,'materialization158.json')]:
  data=json.loads((root/prep).read_bytes());assert data['ids']==['67','E1']
  for n,h in data['copied'].items():assert sha(root/n)==data['changed'].get(n,h),n
  for n,h in data['added'].items():assert sha(root/n)==h,n
 assert (a.asm/'board.sdc').read_bytes()==(e/'asm/board.sdc').read_bytes()
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n158.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(old) as z:
  for n,item in json.loads(z.read('manifest.json'))['files'].items():
   data=z.read(n);assert digest(data)==item['sha256'] and len(data)==item['bytes']
   if n.startswith(('01-GAME157-SD-ROOT/','02-RESTORE044-SD-ROOT/')):
    dest=n.replace('157','158');blobs[dest]=data
    if not n.endswith(('firmware.stm','fpga_n157.bi3')) or n.startswith('02-'):preserved[dest]=digest(data)
 assert digest(blobs['01-GAME158-SD-ROOT/sd2snes/nes/game158.nes'])==ROM_SHA
 assert blobs['01-GAME158-SD-ROOT/NES GAME 158.nh1']==b''
 blobs['01-GAME158-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME158-SD-ROOT/sd2snes/fpga_n158.bi3']=fpga.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game158-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-GAME-158',ids=['67','E1'],physical=False,gameplay_passed=False,ppu_fix='pending-write path model PASS; physical unconfirmed',apu_isolation_retained=True,preserved=preserved,history='last16 consecutive NES clocks retained; pending-write prediction only',limits=['56/56M9K temporary observation','Not physical failure replay or root cause proof','Full IO/MTBF/audio/save/speed remain open'])
 blobs['decision158.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES158-SMB3-CHR-PREVIEW',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/'NES158-SMB3-CHR-PREVIEW.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','decision158.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),fpga_sha256=sha(fpga),normal_trial_ready=True,physical=False,gameplay_passed=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
