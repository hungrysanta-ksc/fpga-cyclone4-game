# SPDX-License-Identifier: MIT
"""Create a private SMB3 trial from pinned164 + tested165 pair, without SD IO."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,ROM_SHA,sha
from nes_cf68_pair_preflight import decode
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','asm','arm','arm-check','coupled','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 arm=json.loads((a.arm_check/'result.json').read_bytes());fpga=json.loads((a.asm/'assembly165.json').read_bytes());coupled=json.loads((a.coupled/'result.json').read_bytes())
 assert arm['passed'] and arm['remaining_margin']>=1024 and coupled['passed'] and fpga['passed']
 for r in [arm,fpga,coupled]:
  for n,h in r['public_sources'].items():assert sha(ROOT/n)==h,n
 assert sha(ROOT/'analysis/runlease165-stack-review.json')==arm['review_sha256']
 for n,h in fpga['preserved'].items():assert sha(a.asm/n)==h,n
 assert fpga['client_sha256']==sha(a.coupled/'client/sink-program.hex')
 assert [c['producer']['frames'] for c in coupled['cases']]==[1,0]
 assert [c['producer']['result'] for c in coupled['cases']]==[0,1]
 assert all(c['consumer']['acks']==45 and c['consumer']['commits']==1 for c in coupled['cases'])
 fw=a.arm/'src/obj-nes-100/firmware.stm';bi=a.asm/'fpga_n165.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(bi)==fpga['packed_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest()
 assert digest(decode(bi.read_bytes()))==fpga['rbf_sha256']
 old=a.baseline/'release/NES164-SMB3-VBLANK-VIDEO.zip'
 v=json.loads((ROOT/'analysis/game164-verification.json').read_bytes())
 assert sha(old)==v['package']['zip_sha256'];blobs={};preserved={}
 with zipfile.ZipFile(old) as z:
  manifest=json.loads(z.read('manifest.json'))
  for n,item in manifest['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith('01-GAME164-SD-ROOT/'):
    rollback=n.replace('01-GAME164-SD-ROOT/','02-RESTORE164-SD-ROOT/');blobs[rollback]=b;preserved[rollback]=digest(b)
    dst=n.replace('164','165');blobs[dst]=b
    if not n.endswith(('firmware.stm','fpga_n164.bi3')):preserved[dst]=digest(b)
 assert digest(blobs['01-GAME165-SD-ROOT/sd2snes/nes/game165.nes'])==ROM_SHA
 assert blobs['01-GAME165-SD-ROOT/NES GAME 165.nh1']==b''
 blobs['01-GAME165-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME165-SD-ROOT/sd2snes/fpga_n165.bi3']=bi.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game165-instructions.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,smooth_60fps=False,selected_fpga='boundary165/map02',selected_mcu='coupled165/arm01',conditional_io_reset_limits_retained=True,run_stack_margin=arm['remaining_margin'],run_limit_ticks=6000,run_sd_writes=False,physical_reset_logging=False,save_sram_used=False,new_map_fit=False,restore='164 exact prior package',next='SMB3 first-level physical AV and menu return; no repeated044 test')
 blobs['decision165.json']=(json.dumps(decision,indent=2)+'\n').encode()
 package='NES165-SMB3-NATIVE-VIDEO';manifest=dict(package=package,files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/(package+'.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision165.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=sha(bi),trial_ready=True,physical=False,preserved=preserved,public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_native165.py','docs/nes-game165-instructions.ko.md']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='preserved'}))
if __name__=='__main__':main()
