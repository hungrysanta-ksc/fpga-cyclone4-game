# SPDX-License-Identifier: MIT
"""Firmware-only221 paired with byte-identical deployed220 FPGA/212 client."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_runtime213 import ROOT,BASE,sha
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-index221';arm=d/'arm01';prep=read(arm/'preparation-index221.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 test=read(d/'test03/result.json');runtime=read(d/'runtime01/result.json');check=read(d/'check01/result.json');budget=read(d/'budget01/result.json')
 for v in [test,runtime,check,budget]:assert v['passed']
 assert test['public_source_sha256']==sha(ROOT/'tools/test_nes_index221.py')
 for n,h in test['inputs'].items():assert sha(BASE/n)==h,n
 for n,h in runtime['source_hashes'].items():
  assert sha(d/'runtime01'/n)==h,n
  if n.startswith('nes_'):assert sha(arm/'src'/n)==h,n
 for n,h in check['public_sources'].items():assert sha(ROOT/n)==h,n
 assert budget['public_source_sha256']==sha(ROOT/'tools/test_nes_index221_budget.py')
 assert budget['budget_sha256']==sha(arm/'src/nes_budget210.c') and budget['menu_sha256']==sha(arm/'src/nes_menu_diagnostic.c')
 assert check['remaining_margin']==1992 and check['irq_reserve']==508
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes()
 assert digest(fw)==check['firmware_sha256'] and sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 for marker in [b'NES GAME 221.nh1',b'game221.nes',b'fpga_n221.bi3',b'nes-progress-221.txt',b'nes-game-last-221.txt',b'nes-budget-221.txt',b'budget_schema=221',b'planner_ticks,callback_ticks',b'd1_payload,d0_clock']:assert marker in fw,marker
 old=BASE/'probes/nes-status220/release01';prior=read(old/'result.json');zpath=old/'NES220-SMB3-WAIT-FIX.zip';assert sha(zpath)==prior['zip_sha256']
 blobs={};preserved={}
 with zipfile.ZipFile(zpath) as z:
  for n,v in read(old/'manifest.json')['files'].items():
   data=z.read(n);assert digest(data)==v['sha256'] and len(data)==v['bytes'],n
   if n.startswith(('01-GAME220-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    new=n.replace('220','221') if n.startswith('01-') else n
    blobs[new]=data
    if not new.endswith('/firmware.stm') or new.startswith('02-'):preserved[new]=digest(data)
 assert digest(blobs['01-GAME221-SD-ROOT/sd2snes/fpga_n221.bi3'])==prior['fpga_sha256']
 blobs['01-GAME221-SD-ROOT/sd2snes/firmware.stm']=fw
 decision=dict(trial_ready=True,physical=False,fps60=False,new_fit=False,new_asm=False,fpga_same220=True,wire_slots_unchanged=True,index_bytes=2816,extra_static_bins=96,remaining_margin=1992,run_ticks=6000,save_sram_unchanged=True,gbc164_unchanged=True)
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game221-ready.ko.md').read_bytes()
 blobs['decision221.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES221-SMB3-INDEX',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 output=a.out/'NES221-SMB3-INDEX.zip'
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
  for n,data in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,17,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
 with zipfile.ZipFile(output) as z:
  assert set(z.namelist())==set(blobs)
  for n,data in blobs.items():assert z.read(n)==data
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 public=['tools/release_nes_index221.py','tools/test_nes_runtime213.py','docs/nes-index221-contract.ko.md','docs/nes-game221-ready.ko.md']
 result=dict(passed=True,decision=decision,zip_sha256=sha(output),firmware_sha256=digest(fw),fpga_sha256=prior['fpga_sha256'],preserved=preserved,
  gates={n:sha(d/n/'result.json') for n in ['test03','runtime01','check01','budget01']},prior_release_sha256=sha(old/'result.json'),
  public_sources=prep['public_sources']|{n:sha(ROOT/n) for n in public},arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin']},
  scope='Synthetic allocator equivalence and actual C RUN tests;220 board/212 client byte-exact reuse. No measured gameplay speed; ingress/scroll-map unchanged.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');(a.out/'manifest.json').write_bytes(blobs['manifest.json'])
 (ROOT/'analysis/index221-verification.json').write_text(json.dumps(dict(test=test,runtime=runtime,budget=budget,release=result),indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,zip_sha256=result['zip_sha256'],firmware_sha256=result['firmware_sha256'],decision=decision)))
if __name__=='__main__':main()
