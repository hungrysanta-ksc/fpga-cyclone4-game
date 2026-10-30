# SPDX-License-Identifier: MIT
"""Private502 capture-correction trial with byte-preserved493 and older restores."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['arm','assembly','prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();v=json.loads((ROOT/'analysis/capture502-release-verification.json').read_text());old=json.loads((ROOT/'analysis/boot493-package.json').read_text())
 assert v['passed']and v['limited_functional_trial_ready']and not v['hardware_verified']
 assert sha(a.prior.read_bytes())==old['ZIP_SHA256']
 fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes();fpga=(a.assembly/'fpga_mmc502.bi3').read_bytes()
 assert sha(fw)==v['ARM']['firmware_SHA256'] and sha(fpga)==v['assembly']['BI3_SHA256']==v['programmer']['image_sha256']
 files={};restores={};active='01-MMC502-SD-ROOT/';before='01-MMC493-SD-ROOT/'
 prefixes=[(before,'02-RESTORE493-SD-ROOT/')]+[(f'{i:02d}-RESTORE{n}-SD-ROOT/',f'{i+1:02d}-RESTORE{n}-SD-ROOT/')for i,n in [(2,489),(3,485),(4,482),(5,476),(6,164),(7,467)]]
 with zipfile.ZipFile(a.prior)as z:
  assert z.testzip()is None
  for n in z.namelist():
   if n.endswith('/'):continue
   for source,dest in prefixes:
    if n.startswith(source):
     b=z.read(n);assert sha(b)==old['files'][n]['SHA256'];name=dest+n[len(source):]
     files[name]=b;restores[name]={'source493_ZIP':n,'SHA256':sha(b)}
  for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:files[active+n]=z.read(before+n)
 files[active+'sd2snes/firmware.stm']=fw;files[active+'sd2snes/fpga_mmc502.bi3']=fpga;files[active+'NES MMC3 502.nh1']=b''
 files[active+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=b'Copy your original mmc493.nes (or480/482/485/489) to mmc502.nes without changing bytes.393232 bytes,CRC32 5a04eed7.\n'
 files['읽어주세요.txt']=(ROOT/'docs/nes-mmc502-trial.ko.md').read_bytes()
 files['verification.json']=(ROOT/'analysis/capture502-release-verification.json').read_bytes()
 files['capture502-verification.json']=(ROOT/'analysis/capture502-verification.json').read_bytes()
 assert restores and not any(n.startswith(active)and n.lower().endswith('.nes')for n in files)
 assert not any(n.lower().endswith(('.srm','.sav','.rtc'))for n in files)
 assert {n for n in files if n.lower().endswith('.nes')}=={'06-RESTORE476-SD-ROOT/sd2snes/nes/nrom476.nes','08-RESTORE467-SD-ROOT/sd2snes/nes/nrom16.nes'}
 assert files['02-RESTORE493-SD-ROOT/sd2snes/firmware.stm']!=fw
 assert sha(files['02-RESTORE493-SD-ROOT/sd2snes/firmware.stm'])==old['firmware_SHA256']
 assert sha(files['02-RESTORE493-SD-ROOT/sd2snes/fpga_mmc493.bi3'])==old['FPGA_SHA256']
 r=dict(passed=True,candidate='MMC502',limited_functional_trial_ready=True,public_release=False,hardware_verified=False,physical_FPS=None,client_ABI='4891',profile_hex='7b',status_version=3,SMB3_ROM_included=False,
  firmware_SHA256=sha(fw),FPGA_SHA256=sha(fpga),baseline493_ZIP_SHA256=old['ZIP_SHA256'],verification_SHA256=sha(files['verification.json']),
  required_ROM=dict(path='sd2snes/nes/mmc502.nes',bytes=393232,CRC32='5a04eed7',SHA256=old['required_ROM']['SHA256']),
  logs=['sd2snes/nes-progress-mmc502.txt','sd2snes/nes-budget-mmc502.txt','sd2snes/nes-game-last-mmc502.txt'],
  restores_byte_preserved=restores,files={n:dict(bytes=len(b),SHA256=sha(b))for n,b in files.items()})
 files['manifest.json']=(json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC502-CAPTURE.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for n,b in files.items():z.writestr(n,b)
 with zipfile.ZipFile(archive)as z:assert z.testzip()is None and set(z.namelist())==set(files)and all(z.read(n)==b for n,b in files.items())
 r.update(ZIP_name=archive.name,ZIP_bytes=archive.stat().st_size,ZIP_SHA256=sha(archive.read_bytes()))
 (a.out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({k:r[k]for k in ['passed','ZIP_name','ZIP_bytes','ZIP_SHA256']}))
