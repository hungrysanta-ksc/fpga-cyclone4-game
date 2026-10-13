# SPDX-License-Identifier: MIT
"""Gate a paired167 trial; keep private ROM/restore assets from166 byte-exact."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import encode,decode
from nes_spi_boot import run
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','fit','quartus-bin','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 ar=json.loads((a.arm_check/'result.json').read_bytes());fit=json.loads((a.fit/'result.json').read_bytes())
 assert ar['passed'] and ar['remaining_margin']>=1024 and fit['passed']
 assert ar['review_sha256']==sha(ROOT/'analysis/pacing167-stack-review.json')
 for v in [ar,fit]:
  for n,h in v['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=json.loads((a.arm/'preparation-pacing167.json').read_bytes())
 for group in ['changed','added']:
  for n,h in prep[group].items():assert sha(a.arm/n)==h,n
 pins=json.loads((a.fit/'preparation.json').read_bytes())['sources']
 for n,h in pins.items():assert sha(a.fit/n)==h,n
 for label,args in [('asm167',['quartus_asm.exe','board']),('cpf167',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],a.fit,label,300)
  assert 'successful' in log and '0 errors' in log,log[-2000:]
 for n,h in pins.items():assert sha(a.fit/n)==h,n
 raw=(a.fit/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.fit/'fpga_n167.bi3').write_bytes(packed)
 assert sha(a.prior)=='cebf7987b0482ef1ecc486439080c2f29a2e543471de9d0bb01e3a4309cc1a0d'
 digest=lambda b:hashlib.sha256(b).hexdigest()
 blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  prior=json.loads(z.read('manifest.json'))
  for n,item in prior['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME166-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('166','167') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME167-SD-ROOT/sd2snes/firmware.stm','01-GAME167-SD-ROOT/sd2snes/fpga_n167.bi3']:preserved[dst]=digest(b)
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 blobs['01-GAME167-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 blobs['01-GAME167-SD-ROOT/sd2snes/fpga_n167.bi3']=packed
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game167-instructions.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,video_fixed_on_hardware=False,frame_rate_approved=False,run_ticks=6000,run_sd_writes=False,save_sram_used=False,trace_bytes=48,stack_margin=ar['remaining_margin'],fill_total_cycles=16777216,export_total_cycles=33554432,short_wait_cycles=131072,short_wait_excludes=['REQUEST','STREAM'],accepted_read_arbiter_watchdog_unchanged=True,abort_byte='fill_error high4; export_error low4',full_external_io_approved=False)
 blobs['decision167.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES167-SMB3-FILL-WAIT',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES167-SMB3-FILL-WAIT.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision167.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(packed),rbf_sha256=digest(raw),preserved=preserved,public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_pacing167.py','docs/nes-game167-instructions.ko.md','tools/nes_pacing167_mcu.py','analysis/pacing167-stack-review.json']},physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='preserved'}))
if __name__=='__main__':main()
