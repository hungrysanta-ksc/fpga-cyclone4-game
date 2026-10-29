# SPDX-License-Identifier: MIT
"""Private485 ARM trial with byte-identical482 FPGA and482/476/164/467 restores."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda q:json.loads(q.read_text(encoding='utf8'))
p=argparse.ArgumentParser(description=__doc__)
for n in ['arm','prior','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();r=read(ROOT/'analysis/supply485-verification.json');old=read(ROOT/'analysis/mmc482-package.json')
assert r['passed'] and r['hardware_trial_ready'] and not r['hardware_verified']
assert sha(a.prior.read_bytes())==old['ZIP_SHA256']
fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes();assert sha(fw)==r['ARM']['firmware_SHA256']
files={};restores={};active='01-MMC485-SD-ROOT/';old_active='01-MMC482-BOOTDIAG-SD-ROOT/'
with zipfile.ZipFile(a.prior) as z:
    for n in z.namelist():
        if n.startswith(old_active) and not n.endswith('/'):
            data=z.read(n);dest='02-RESTORE482-SD-ROOT/'+n[len(old_active):]
            files[dest]=data;restores[dest]={'source482':n,'SHA256':sha(data)}
            assert sha(data)==old['files'][n]['SHA256']
        for old_prefix,new_prefix in [('02-RESTORE476','03-RESTORE476'),('03-RESTORE164','04-RESTORE164'),('04-RESTORE467','05-RESTORE467')]:
            if n.startswith(old_prefix+'-SD-ROOT/') and not n.endswith('/'):
                data=z.read(n);dest=new_prefix+n[len(old_prefix):]
                assert sha(data)==old['files'][n]['SHA256'];files[dest]=data;restores[dest]={'source482':n,'SHA256':sha(data)}
    for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:files[active+n]=z.read(old_active+n)
    fpga=z.read(old_active+'sd2snes/fpga_mmc482.bi3')
assert sha(fpga)==r['FPGA']['BI3_SHA256']
files[active+'sd2snes/firmware.stm']=fw;files[active+'sd2snes/fpga_mmc485.bi3']=fpga
files[active+'NES MMC3 485.nh1']=b''
files[active+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=b'Copy original mmc480.nes or mmc482.nes as mmc485.nes.393232 bytes,CRC32 5a04eed7.No ROM patch.\n'
files['읽어주세요.txt']=(ROOT/'docs/nes-mmc485-trial.ko.md').read_bytes()
files['verification.json']=(ROOT/'analysis/supply485-verification.json').read_bytes()
assert restores and not any(n.startswith(active) and n.lower().endswith('.nes') for n in files)
manifest={'candidate':'MMC485','private_trial_ready':True,'public_release':False,'hardware_verified':False,
          'physical_FPS':None,'profile_hex':'7b','status_version':3,'SMB3_ROM_included':False,
          'firmware_SHA256':sha(fw),'FPGA_SHA256':sha(fpga),'FPGA_byte_identical_to482':True,
          'required_ROM':{'path':'sd2snes/nes/mmc485.nes','bytes':393232,'CRC32':'5a04eed7',
                          'SHA256':'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'},
          'restores_byte_preserved':restores,'files':{n:{'bytes':len(b),'SHA256':sha(b)} for n,b in files.items()}}
files['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC485-SUPPLY.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in files.items():z.writestr(n,b)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None and set(z.namelist())==set(files)
    assert all(z.read(n)==b for n,b in files.items())
result=dict(manifest,passed=True,ZIP_name=archive.name,ZIP_bytes=archive.stat().st_size,ZIP_SHA256=sha(archive.read_bytes()),baseline482_ZIP_SHA256=old['ZIP_SHA256'])
(a.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps({k:result[k] for k in ['passed','ZIP_name','ZIP_bytes','ZIP_SHA256']}))
