# SPDX-License-Identifier: MIT
"""Package selected222 startup changes with unchanged221 frame path/220 FPGA."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_runtime213 import ROOT,BASE,sha
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-startup222';arm=d/'arm02';prep=read(arm/'preparation-startup222.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 test=read(d/'test03/result.json');check=read(d/'check03/result.json');rtl=read(d/'rtl01/result.json')
 assert test['passed'] and check['passed'] and rtl['passed']
 assert test['public_source_sha256']==sha(ROOT/'tools/test_nes_startup222.py')
 for n,h in test['source_pins'].items():assert sha(arm/'src'/n)==h,n
 assert test['rtl_reply_sha256']==rtl['replies_sha256']==sha(d/'rtl01/replies.txt')
 assert rtl['source_sha256']==sha(ROOT/'tools/test_nes_startup222_bridge.py')
 for n,h in rtl['rtl_pins'].items():assert sha(BASE/'probes/nes-status220/source02'/n)==h,n
 assert rtl['rom_sha256']==sha(BASE/'probes/nes-runtime213/asm01/sink-program.hex')
 for n,h in check['public_sources'].items():assert sha(ROOT/n)==h,n
 assert check['remaining_margin']==1912 and check['startup_local_stack_bytes']==32
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes()
 assert digest(fw)==check['firmware_sha256'] and sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 for marker in [b'NES GAME 222.nh1',b'game222.nes',b'fpga_n222.bi3',b'nes-progress-222.txt',b'nes-game-last-222.txt',b'nes-budget-222.txt',b'budget_schema=222',b'startup_schema=222',b'startup_post_reply_hex=']:assert marker in fw,marker
 unchanged=['nes_native_runtime165.c','nes_native_runtime165.h','nes_resident211.c','nes_resident211.h','nes_planner211.c','nes_sink_window184.c','nes_native165_bulk.inc','nes_boot214.inc','nes_cf86_session094.c']
 reused={}
 for n in unchanged:
  assert sha(arm/'src'/n)==sha(BASE/'probes/nes-index221/arm01/src'/n),n
  reused[n]=sha(arm/'src'/n)
 old=BASE/'probes/nes-index221/release01';prior=read(old/'result.json');zpath=old/'NES221-SMB3-INDEX.zip';assert sha(zpath)==prior['zip_sha256']
 blobs={};preserved={}
 with zipfile.ZipFile(zpath) as z:
  for n,v in read(old/'manifest.json')['files'].items():
   data=z.read(n);assert digest(data)==v['sha256'] and len(data)==v['bytes'],n
   if n.startswith(('01-GAME221-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    new=n.replace('221','222') if n.startswith('01-') else n;blobs[new]=data
    if not new.endswith('/firmware.stm') or new.startswith('02-'):preserved[new]=digest(data)
 assert digest(blobs['01-GAME222-SD-ROOT/sd2snes/fpga_n222.bi3'])==prior['fpga_sha256']
 blobs['01-GAME222-SD-ROOT/sd2snes/firmware.stm']=fw
 decision=dict(trial_ready=True,physical=False,root_cause_proven=False,fps60=False,new_fit=False,new_asm=False,
  fpga_same220=True,index_same221=True,startup_local_stack=32,frame_local_stack=31848,remaining_margin=1912,
  extra_static_bytes=56,extra_spi_bytes_max=40,run_ticks=6000,save_sram_unchanged=True,gbc164_unchanged=True)
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game222-ready.ko.md').read_bytes()
 blobs['nes-startup222-contract.ko.md']=(ROOT/'docs/nes-startup222-contract.ko.md').read_bytes()
 blobs['decision222.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES222-SMB3-STARTUP',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 output=a.out/'NES222-SMB3-STARTUP.zip'
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
  for n,data in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,17,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
 with zipfile.ZipFile(output) as z:
  assert set(z.namelist())==set(blobs)
  for n,data in blobs.items():assert z.read(n)==data
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 public=['tools/release_nes_startup222.py','tools/test_nes_startup222.py','tools/test_nes_startup222_bridge.py','tools/check_nes_startup222_arm.py','docs/nes-startup222-contract.ko.md','docs/nes-game222-ready.ko.md']
 result=dict(passed=True,decision=decision,zip_sha256=sha(output),firmware_sha256=digest(fw),fpga_sha256=prior['fpga_sha256'],preserved=preserved,
  gates={n:sha(d/n/'result.json') for n in ['test03','rtl01','check03']},unchanged_selected221_sources=reused,
  reused221_gates={n:sha(BASE/'probes/nes-index221'/n/'result.json') for n in ['test03','runtime01']},
  public_sources=prep['public_sources']|{n:sha(ROOT/n) for n in public},
  arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin']},
  scope='Actual C startup/cleanup and real RTL SPI reply replay, platform/runtime fixtures. Identical221 game path reuses prior tests. Physical reset timing and221 root cause unproven.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');(a.out/'manifest.json').write_bytes(blobs['manifest.json'])
 (ROOT/'analysis/startup222-verification.json').write_text(json.dumps(dict(test=test,bridge=rtl,release=result),indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,zip_sha256=result['zip_sha256'],firmware_sha256=result['firmware_sha256'],decision=decision)))
if __name__=='__main__':main()
