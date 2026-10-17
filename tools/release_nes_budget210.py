# SPDX-License-Identifier: MIT
"""Package checked210 ARM with byte-identical209 FPGA/client/restoration.
No new FIT/ASM. Refuse mismatched selected source, test, report or linked ELF.
"""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_budget210 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
PUBLIC=['tools/nes_budget210.py','tools/test_nes_budget210.py','tools/check_nes_budget210_arm.py',
 'tools/analyze_nes_budget210.py','tools/release_nes_budget210.py',
 'src/nes/firmware/nes_budget210.c','src/nes/firmware/nes_budget210.h',
 'docs/nes-budget210-contract.ko.md','docs/nes-game210-ready.ko.md']
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-budget210';arm=d/'arm03';prep=read(arm/'preparation-budget210.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 test=read(d/'test05/result.json');check=read(d/'check02/result.json');report=read(d/'report02/result.json')
 assert all(x['passed'] for x in [test,check,report]) and check['remaining_margin']>=1024
 for item in [test,check]:
  for n,h in item['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in test['changed_sources'].items():assert sha(arm/'src'/n)==h,n
 assert test['menu_source']==report['source_sha256']==sha(arm/'src/nes_menu_diagnostic.c')
 assert 'bytes=4047 capacity=4096' in report['output'] and 'format_bytes=2420' in test['unit']
 assert 'save_tail persist_gate=1 irq_restore=2 errors=2 same_buffer=1' in test['save_test']
 assert sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==check['firmware_sha256']
 for m in [b'NES GAME 210.nh1',b'game210.nes',b'fpga_n210.bi3',b'nes-progress-210.txt',b'nes-game-last-210.txt',b'nes-budget-210.txt',b'NES-GAME210-DEV']:assert m in fw,m
 for m in [b'NES GAME 209.nh1',b'game209.nes',b'fpga_n209.bi3']:assert m not in fw,m
 archive=verify_archive('nes-binding209');assert archive['manifest_sha256']=='a1d60c407092c39a371f3909cc0bc6c16187f941eba7b2d47cfb361e4edecbd7'
 old=BASE/'probes/nes-binding209/release01';old_result=read(old/'result.json');zpath=old/'NES209-SMB3-DIRECT-TILES.zip'
 assert sha(zpath)==old_result['zip_sha256'] and old_result['decision']['trial_ready']
 blobs={};preserved={}
 with zipfile.ZipFile(zpath) as z:
  for n,item in read(old/'manifest.json')['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
   if n.startswith(('01-GAME209-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('209','210') if n.startswith('01-') else n;blobs[dst]=b
    if dst!='01-GAME210-SD-ROOT/sd2snes/firmware.stm':preserved[dst]=digest(b)
 blobs['01-GAME210-SD-ROOT/sd2snes/firmware.stm']=fw
 assert digest(blobs['01-GAME210-SD-ROOT/sd2snes/fpga_n210.bi3'])==old_result['fpga_sha256']
 assert digest(blobs['01-GAME210-SD-ROOT/sd2snes/nes/game210.nes'])=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
 assert blobs['01-GAME210-SD-ROOT/NES GAME 210.nh1']==b''
 decision=dict(trial_ready=True,physical=False,fps60_proven=False,new_fit=False,new_asm=False,
  fpga_byte_identical209=True,run_ticks=6000,remaining_margin=check['remaining_margin'],
  state_bytes=check['budget_bytes'],run_only_cache_bytes=2560,save_sram_used=False,
  report_bytes=4047,budget_report_max_bytes=2420,scope='Sorted lookup plus passive256-entry ROM reuse model and5s frame-start runtime SPI bins. Not persistent production slots or actual scroll performance proof.')
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game210-ready.ko.md').read_bytes()
 blobs['decision210.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES210-SMB3-SCROLL-BUDGET',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);zout=a.out/'NES210-SMB3-SCROLL-BUDGET.zip'
 with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,17,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(zout) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 r=dict(passed=True,selected=['arm03','test05','check02','report02','release01'],decision=decision,
  zip_sha256=sha(zout),firmware_sha256=digest(fw),fpga_sha256=old_result['fpga_sha256'],preserved=preserved,
  prior_archive=archive,prior_release_sha256=sha(old/'result.json'),
  gates={n:sha(d/n/'result.json') for n in ['test05','check02','report02']},
  public_sources={n:sha(ROOT/n) for n in PUBLIC},new_arm=True,new_fit=False,new_asm=False,actual_scroll_measured=False,
  next='User210 first-level continuous scroll, threeTXT plus video/time context. Classify bins before candidate reuse/geometry budget; no60fps claim or old209/044/pad-only repeat.')
 for n,b in [('result.json',(json.dumps(r,indent=2)+'\n').encode()),('manifest.json',blobs['manifest.json']),('START-HERE.ko.md',blobs['START-HERE.ko.md'])]:(a.out/n).write_bytes(b)
 (ROOT/'analysis/budget210-verification.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,zip_sha256=r['zip_sha256'],firmware_sha256=r['firmware_sha256'],decision=decision)))
if __name__=='__main__':main()
