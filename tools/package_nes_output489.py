# SPDX-License-Identifier: MIT
"""Private paired489 trial; byte-preserve485/482/476/164/467 restores, no ROM."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
p=argparse.ArgumentParser(description=__doc__)
for n in ['arm','assembly','prior','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();v=json.loads((ROOT/'analysis/output489-verification.json').read_text());old=json.loads((ROOT/'analysis/supply485-package.json').read_text())
assert v['passed'] and v['limited_hardware_trial_ready'] and not v['hardware_verified'] and v['FPGA']['related_timing_passed']
assert sha(a.prior.read_bytes())==old['ZIP_SHA256']
fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes();fpga=(a.assembly/'fpga_mmc489.bi3').read_bytes()
assert sha(fw)==v['ARM']['firmware_SHA256'] and sha(fpga)==v['assembly']['BI3_SHA256']
files={};restores={};active='01-MMC489-SD-ROOT/';oldactive='01-MMC485-SD-ROOT/'
prefixes=[(oldactive,'02-RESTORE485-SD-ROOT/'),('02-RESTORE482-SD-ROOT/','03-RESTORE482-SD-ROOT/'),('03-RESTORE476-SD-ROOT/','04-RESTORE476-SD-ROOT/'),('04-RESTORE164-SD-ROOT/','05-RESTORE164-SD-ROOT/'),('05-RESTORE467-SD-ROOT/','06-RESTORE467-SD-ROOT/')]
with zipfile.ZipFile(a.prior)as z:
 for n in z.namelist():
  if n.endswith('/'):continue
  for before,after in prefixes:
   if n.startswith(before):
    b=z.read(n);assert sha(b)==old['files'][n]['SHA256'];dest=after+n[len(before):];files[dest]=b;restores[dest]={'source485_ZIP':n,'SHA256':sha(b)}
 for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:files[active+n]=z.read(oldactive+n)
files[active+'sd2snes/firmware.stm']=fw;files[active+'sd2snes/fpga_mmc489.bi3']=fpga;files[active+'NES MMC3 489.nh1']=b''
files[active+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=b'Copy your original mmc480.nes/mmc482.nes/mmc485.nes as mmc489.nes without changing bytes.393232 bytes,CRC32 5a04eed7.\n'
files['읽어주세요.txt']=(ROOT/'docs/nes-mmc489-trial.ko.md').read_bytes();files['verification.json']=(ROOT/'analysis/output489-verification.json').read_bytes()
assert len(restores)>0 and not any(n.startswith(active)and n.lower().endswith('.nes')for n in files)
assert not any(n.lower().endswith(('.srm','.sav','.rtc'))for n in files)
assert {n for n in files if n.lower().endswith('.nes')}=={'04-RESTORE476-SD-ROOT/sd2snes/nes/nrom476.nes','06-RESTORE467-SD-ROOT/sd2snes/nes/nrom16.nes'}
r={'passed':True,'candidate':'MMC489','private_trial_ready':True,'public_release':False,'hardware_verified':False,'physical_FPS':None,'profile_hex':'7b','status_version':3,'client_ABI':'4891','SMB3_ROM_included':False,'firmware_SHA256':sha(fw),'FPGA_SHA256':sha(fpga),'baseline485_ZIP_SHA256':old['ZIP_SHA256'],'required_ROM':{'path':'sd2snes/nes/mmc489.nes','bytes':393232,'CRC32':'5a04eed7','SHA256':'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'},'restores_byte_preserved':restores,'files':{n:{'bytes':len(b),'SHA256':sha(b)}for n,b in files.items()}}
files['manifest.json']=(json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode('utf8')
a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC489-RAWDMA.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in files.items():z.writestr(n,b)
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None and set(z.namelist())==set(files) and all(z.read(n)==b for n,b in files.items())
r.update(ZIP_name=archive.name,ZIP_bytes=archive.stat().st_size,ZIP_SHA256=sha(archive.read_bytes()))
(a.out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:r[k]for k in ['passed','ZIP_name','ZIP_bytes','ZIP_SHA256']}))
