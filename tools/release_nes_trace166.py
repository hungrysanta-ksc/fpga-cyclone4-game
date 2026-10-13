# SPDX-License-Identifier: MIT
"""Private166 observation package, byte-identical165 FPGA/164 restore."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,sha
from test_nes_native_runtime165 import MODULES
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','test','wait','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 ar=json.loads((a.arm_check/'result.json').read_bytes());t=json.loads((a.test/'result.json').read_bytes());w=json.loads((a.wait/'result.json').read_bytes())
 assert ar['passed'] and ar['remaining_margin']>=1024 and t['passed'] and w['passed']
 assert t['dirty_wram_bytes']==131072 and t['consumer']['acks']==45 and t['producer']['frames']==1
 assert ar['review_sha256']==sha(ROOT/'analysis/trace166-stack-review.json')
 for v in [ar,t,w]:
  for n,h in v['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in MODULES+['nes_trace166']:
  for ext in ['c','h']:assert (a.arm/'src'/(n+'.'+ext)).read_text()==(a.test/(n+'.'+ext)).read_text(),n
 prep=json.loads((a.arm/'preparation-trace166.json').read_bytes())
 for group in ['changed','added']:
  for n,h in prep[group].items():assert sha(a.arm/n)==h,n
 assert sha(a.prior)=='702ca2f77e2ca6ff29846ba1b2b3877f90afb8f980efbe53da9684c13d587787'
 digest=lambda b:hashlib.sha256(b).hexdigest()
 blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  prior=json.loads(z.read('manifest.json'))
  for n,item in prior['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME165-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('165','166') if n.startswith('01-') else n;blobs[dst]=b
    if not dst.endswith('01-GAME166-SD-ROOT/sd2snes/firmware.stm'):preserved[dst]=digest(b)
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 blobs['01-GAME166-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game166-instructions.ko.md').read_bytes()
 decision=dict(trial_ready=True,video_fixed=False,physical=False,fpga_unchanged=True,run_ticks=6000,run_sd_writes=False,save_sram_used=False,trace_bytes=48,stack_margin=ar['remaining_margin'],next='One SMB3 trial to distinguish no BEGIN from repeated ABORT; no video or044 repeat needed.')
 blobs['decision166.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES166-SMB3-FRAME-TRACE',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES166-SMB3-FRAME-TRACE.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision166.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(blobs['01-GAME166-SD-ROOT/sd2snes/fpga_n166.bi3']),preserved=preserved,public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_trace166.py','docs/nes-game166-instructions.ko.md','tools/nes_trace166.py','analysis/trace166-stack-review.json']},video_fixed=False,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='preserved'}))
if __name__=='__main__':main()
