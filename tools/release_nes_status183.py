# SPDX-License-Identifier: MIT
"""Package checked next-block status reuse, preserving182 DMA/FPGA/SNES."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,sha
from nes_status183 import receiver,header
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','check','test','report','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();load=lambda p:json.loads(p.read_bytes());digest=lambda b:hashlib.sha256(b).hexdigest()
 assert sha(a.prior)=='beedfca4fb0033b8f973f6128499525a2c463e37c9dee2cc3579d434682c928e'
 prep=load(a.arm/'preparation-status183.json');pins=prep['copied']|prep['changed']|prep['added']
 assert set(prep['changed'])=={'src/nes_native165.c','src/nes_native165.h','src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION'} and not prep['added']
 for n,h in pins.items():assert sha(a.arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 results={k:load(d/'result.json') for k,d in [('check',a.check),('test',a.test),('report',a.report)]}
 assert all(r['passed'] for r in results.values());check=results['check'];assert check['remaining_margin']>=1024
 for k in ['check','test']:
  for n,h in results[k]['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in results['test']['source_pins'].items():assert sha(a.arm/'src'/n)==h,n
 baseline=ROOT.parent/'probes/nes-dma182/arm02/src'
 assert (a.arm/'src/nes_native165.c').read_text()==receiver((baseline/'nes_native165.c').read_text())
 assert (a.arm/'src/nes_native165.h').read_text()==header((baseline/'nes_native165.h').read_text())
 for n in ['nes_native_sink165.c','nes_native_sink165.h','nes_native_video165.c','nes_native_video165.h','nes_dma182.inc','nes_native165_bulk.inc']:
  assert (a.arm/'src'/n).read_bytes()==(baseline/n).read_bytes(),n
 spi=ROOT.parent/'probes/nes-checkstate181/evidence/map01/nes_native_spi165.sv'
 assert sha(spi)==sha(ROOT.parent/'probes/nes-packed181/evidence/test02/nes_native_spi165.sv')=='e62e3c62a7cb04a787c3bae8beb54765ca8728db9adfe99927de6d2f24ea9b73'
 assert sha(a.arm/'src/nes_menu_diagnostic.c')==results['report']['source_sha256']
 fw=(a.arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==check['firmware_sha256']
 for marker in [b'NES GAME 183.nh1',b'fpga_n183.bi3',b'game183.nes',b'nes-progress-183.txt',b'nes-game-last-183.txt']:assert marker in fw,marker
 blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  for n,item in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
   if n.startswith(('01-GAME182-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dest=n.replace('182','183') if n.startswith('01-') else n;blobs[dest]=b
    if not dest.endswith('/firmware.stm') or dest.startswith('02-'):preserved[dest]=digest(b)
 blobs['01-GAME183-SD-ROOT/sd2snes/firmware.stm']=fw;blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game183-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,fps60_proven=False,firmware_only=True,fpga_unchanged=True,additional_static_bytes=0,additional_run_bytes=8,remaining_margin=check['remaining_margin'],spi_hz=2625000,run_ticks=6000,save_sram_used=False,chr_batch_candidate_adopted=False)
 blobs['decision183.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES183-SMB3-STATUS-VIDEO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/'NES183-SMB3-STATUS-VIDEO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,15,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 result=dict(passed=True,zip_sha256=sha(archive),firmware_sha256=digest(fw),firmware_bytes=len(fw),preserved=preserved,decision=decision,source_pins=len(pins),gates={k:sha(d/'result.json') for k,d in [('check',a.check),('test',a.test),('report',a.report)]},public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_status183.py','docs/nes-game183-ready.ko.md']})
 for n,b in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('manifest.json',blobs['manifest.json']),('START-HERE.ko.md',blobs['START-HERE.ko.md'])]:(a.out/n).write_bytes(b)
 print(json.dumps({k:v for k,v in result.items() if k!='preserved'}))
if __name__=='__main__':main()
