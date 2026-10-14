# SPDX-License-Identifier: MIT
"""173 MCU-only timing trial. Exact172 FPGA and164 restoration are mandatory."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','test','report','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 load=lambda p:json.loads(p.read_bytes())
 ar=load(a.arm_check/'result.json');t=load(a.test/'result.json');rp=load(a.report/'result.json')
 assert all(x['passed'] for x in [ar,t,rp]) and ar['remaining_margin']>=1024
 for x in [ar,t]:
  for n,h in x['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in t['source_sha256'].items():assert sha(a.arm/'src'/n)==h,n
 assert rp['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 prep=load(a.arm/'preparation-profile173.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(a.arm/n)==h,n
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 assert sha(a.prior)=='48513f0cd1a5b44ad2acd248e09697b7b615b08496f2bf0b473ef0e92d0defd7'
 digest=lambda b:hashlib.sha256(b).hexdigest()
 blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  for n,q in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert digest(b)==q['sha256'] and len(b)==q['bytes']
   if n.startswith(('01-GAME172-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('172','173') if n.startswith('01-') else n;blobs[dst]=b
    if dst!='01-GAME173-SD-ROOT/sd2snes/firmware.stm':preserved[dst]=digest(b)
 bit='01-GAME173-SD-ROOT/sd2snes/fpga_n173.bi3'
 assert digest(blobs[bit])=='6e9f7fc0577d9e070476444ab04b9fe4fd05f811c0bbb81818168bcac8288b74'
 assert b'ppu_history_kind=' in fw.read_bytes() and b'A3_FIRST_REJECT' not in fw.read_bytes()
 blobs['01-GAME173-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game173-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,root_cause_fixed=False,continuous_video_proven=False,
  fpga='byte-exact172',trace_schema=173,ppu_history_schema=157,profile_tick_ms=10,
  run_ticks_after_ready=6000,run_sd_writes=False,save_sram_used=False,remaining_margin=ar['remaining_margin'])
 blobs['decision173.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest={'package':'NES173-SMB3-VIDEO-PROFILE','files':{n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()}}
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES173-SMB3-VIDEO-PROFILE.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b
 assert all(digest(blobs[n])==h for n,h in preserved.items())
 result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,
  firmware_sha256=sha(fw),fpga_sha256=digest(blobs[bit]),preserved=preserved,decision=decision,
  public_sources={'tools/release_nes_profile173.py':sha(Path(__file__))})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
