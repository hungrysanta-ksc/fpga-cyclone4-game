# SPDX-License-Identifier: MIT
"""Package unchanged090 firmware after091 transition proof; no SD installation."""
from pathlib import Path
import argparse,json
from package_nes_report084 import make_zip,digest,RESTORE,OFFLINE
from nes_report084_prepare import ROOT,sha
FW='00f757fcd1ca0da08ce0e5564358e06b482071e6119d8827e6c81748fcfddebe'
PIN='5ecbc6fe3f5580943d0a9d991d880595caa1d30db37cb78815114bc2c42f0512'
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence090','evidence075','pins','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence090.resolve();o=a.out.resolve();assert not o.exists();o.mkdir(parents=True)
 assert sha(e/'manifest.json')==PIN
 inventory=json.loads((e/'manifest.json').read_bytes())['files']
 def read(n):assert sha(e/n)==inventory[n],n;return (e/n).read_bytes()
 arm=json.loads(read('arm01/arm-check090.json'));assert arm['firmware_sha256']==FW
 fw=read('arm01/source/src/obj-report079/firmware.stm');assert digest(fw)==FW and len(fw)==196248
 result=json.loads((a.pins/'result.json').read_bytes());assert result['checks']==94 and not result['production_changed']
 for n,h in result['files'].items():assert sha(a.pins/n)==h,n
 for n in arm['host_same']:assert sha(a.pins/n)==sha(e/'arm01/source/src'/n),n
 assert result['configuration_rising_edges_per_success']==6543555
 assert sha(a.evidence075/'manifest.json')==OFFLINE
 restore=a.evidence075/'inputs/firmware.stm';assert sha(restore)==RESTORE and restore.stat().st_size==169056
 source=e/'arm01/source'
 files={'test/sd2snes/firmware.stm':fw,'restore/sd2snes/firmware.stm':restore.read_bytes(),'README.ko.md':(ROOT/'docs/CLOCKREPORT090-RUN.ko.md').read_bytes(),'LICENSE.txt':read('arm01/source/LICENSE')}
 manifest=dict(candidate='CLOCKREPORT090',packaging_milestone='091',purpose='RESET-held reference clock observation; not game firmware',automatic_install=False,physical_verified=False,firmware_unchanged_from090=True,files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in files.items()},cf87_rle_sha256=arm['embedded_rle_sha256'],restore_role='exact user-supplied normal044; prior menu/GBC physical PASS')
 files['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode();trial=make_zip(o/'FXPAK-CLOCKREPORT090-TRIAL.zip',files)
 prep=json.loads(read('arm01/preparation090.json'));sources={}
 for n,h in prep['files'].items():
  b=read('arm01/source/'+n)
  if n=='src/.ARG_VERSION':assert b.decode()=='"CLOCKREPORT090"'
  else:assert digest(b)==h,n
  assert digest(b)!='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
  sources['source/'+n]=b
 for n in ['cfgware.h','autoconf.h']:sources['build-inputs/'+n]=read('arm01/source/src/obj-report079/'+n)
 for n in ['nes_clock_report090_prepare.py','build_nes_report079_arm.ps1','check_nes_clock_report090_arm.py','package_nes_clock091.py','package_nes_report084.py','nes_report084_prepare.py']:
  sources['tools/'+n]=(ROOT/'tools'/n).read_bytes()
 sources['BUILD-NOTES.txt']=b'CLOCKREPORT090 unchanged. ARM GNU13.3.Rel1 Cortex-M4. Build prepared source with build_nes_report079_arm.ps1 and source/verilog/sd2snes_mini/fpga_mini.bi3. Output obj-report079 name is historical; VERSION is CLOCKREPORT090. Use source/src/clock089_payload.h as supplied. External make/hostGCC/Unix tools and ARM compiler required. source archive contains original LICENSE/notices. No proprietary target game ROM included. Physical clock return pending.\n'
 sourcezip=make_zip(o/'FXPAK-CLOCKREPORT090-SOURCE.zip',sources)
 result=dict(candidate='CLOCKREPORT090',milestone='091',trial=trial,source=sourcezip,firmware_sha256=FW,restore_sha256=RESTORE,member_readback=True,report_trial_ready=True,nes_installable=False,hardware_verified=False,installed=False)
 (o/'package-check091.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ['candidate','firmware_sha256','restore_sha256','member_readback','report_trial_ready','nes_installable']}))
if __name__=='__main__':main()
