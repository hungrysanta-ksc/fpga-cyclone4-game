# SPDX-License-Identifier: MIT
"""Package215 first invalid E8 evidence, unchanged214 FPGA/game renderer."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_runtime213 import ROOT,BASE,sha
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-plan215';arm=d/'arm01';prep=read(arm/'preparation-plan215.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 check=read(d/'check01/result.json');unit=read(d/'test03/result.json');boot=read(d/'boot01/result.json');rtl=read(d/'rtl02/result.json')
 assert all(x['passed'] for x in [check,unit,boot,rtl])
 assert check['remaining_margin']==4952 and 'checks=1600 retained_bytes=30 format_max=2782' in unit['output']
 assert boot['cases']==11 and rtl['codes']==[0,0]
 assert 'PASS PLAN215 frames=20' in (d/'rtl02/host.log').read_text()
 for report in [unit,boot]:
  for n,h in report['source_pins'].items():assert sha(arm/'src'/n)==h,n
 assert unit['public_sha']==sha(ROOT/'tools/test_nes_plan215.py')
 assert boot['source_sha256']==sha(ROOT/'tools/test_nes_plan215_boot.py')
 assert rtl['public_sha']==sha(ROOT/'tools/test_nes_plan215_rtl.py')
 for n,h in rtl['source_pins'].items():
  f=Path(n);assert sha(f if f.is_absolute() else BASE/f)==h,n
 for n,h in check['public_sources'].items():assert sha(ROOT/n)==h,n
 old=BASE/'probes/nes-startup214/release01';oldr=read(old/'result.json');oldz=old/'NES214-SMB3-BOOT-CAUSE.zip';assert sha(oldz)==oldr['zip_sha256']
 blobs={};preserved={}
 with zipfile.ZipFile(oldz) as z:
  for n,item in read(old/'manifest.json')['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME214-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('214','215') if n.startswith('01-') else n;blobs[dst]=b
    if dst!='01-GAME215-SD-ROOT/sd2snes/firmware.stm':preserved[dst]=digest(b)
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==check['firmware_sha256'];assert sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 for m in [b'NES GAME 215.nh1',b'game215.nes',b'fpga_n215.bi3',b'nes-progress-215.txt',b'nes-game-last-215.txt',b'nes-budget-215.txt',b'plan_reply_hex=',b'boot_reason=']:assert m in fw,m
 blobs['01-GAME215-SD-ROOT/sd2snes/firmware.stm']=fw;fpga=digest(blobs['01-GAME215-SD-ROOT/sd2snes/fpga_n215.bi3']);assert fpga==oldr['fpga_sha256']
 decision=dict(trial_ready=True,root_cause_fixed=False,physical=False,new_fit=False,new_asm=False,unchanged214_fpga=True,unchanged214_renderer=True,remaining_margin=4952,record_bytes=30,added_static_bytes=32,budget_max=2782,run_ticks=6000,extra_spi_requests=0,first_error_only=True)
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game215-ready.ko.md').read_bytes();blobs['decision215.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES215-SMB3-PLAN-CAUSE',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()});blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 zout=a.out/'NES215-SMB3-PLAN-CAUSE.zip'
 with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,17,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(zout) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 public=['tools/nes_plan215.py','tools/test_nes_plan215.py','tools/test_nes_plan215_boot.py','tools/test_nes_plan215_rtl.py','tools/check_nes_plan215_arm.py','tools/release_nes_plan215.py','src/nes/firmware/nes_plan215.h','tests/nes-functional/plan215_host.c','docs/nes-game215-ready.ko.md','docs/nes-plan215-contract.ko.md']
 r=dict(passed=True,decision=decision,firmware_sha256=digest(fw),fpga_sha256=fpga,zip_sha256=sha(zout),preserved=preserved,prior214_zip_sha256=sha(oldz),gates={n:sha(d/n/'result.json') for n in ['check01','test03','boot01','rtl02']},public_sources={n:sha(ROOT/n) for n in public},arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin']},rtl_output=(d/'rtl02/host.log').read_text())
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(a.out/'manifest.json').write_bytes(blobs['manifest.json']);(ROOT/'analysis/plan215-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,zip_sha256=r['zip_sha256'],decision=decision)))
if __name__=='__main__':main()
