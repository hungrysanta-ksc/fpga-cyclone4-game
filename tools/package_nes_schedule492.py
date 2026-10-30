# SPDX-License-Identifier: MIT
"""Paired492 real-schedule trial; preserve489 and older restores byte-for-byte."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','assembly','prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();v=json.loads((ROOT/'analysis/schedule492-verification.json').read_text());old=json.loads((ROOT/'analysis/output489-package.json').read_text())
    assert v['passed'] and v['limited_functional_trial_ready'] and not v['physical_acceleration_verified']
    assert sha(a.prior.read_bytes())==old['ZIP_SHA256']
    fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes();fpga=(a.assembly/'fpga_mmc492.bi3').read_bytes()
    assembly=json.loads((a.assembly/'result.json').read_text());assert assembly['passed']
    assert sha(fw)==v['ARM']['firmware_SHA256'] and sha(fpga)==v['programmer']['image_sha256']==assembly['BI3_SHA256']
    assert assembly['source_inputs']==v['FPGA']['source_inputs']
    files={};restores={};active='01-MMC492-SD-ROOT/';before='01-MMC489-SD-ROOT/'
    prefixes=[(before,'02-RESTORE489-SD-ROOT/')]+[(f'{i:02d}-RESTORE{n}-SD-ROOT/',f'{i+1:02d}-RESTORE{n}-SD-ROOT/')for i,n in [(2,485),(3,482),(4,476),(5,164),(6,467)]]
    with zipfile.ZipFile(a.prior)as z:
        for n in z.namelist():
            if n.endswith('/'):continue
            for source,dest in prefixes:
                if n.startswith(source):
                    b=z.read(n);assert sha(b)==old['files'][n]['SHA256'];name=dest+n[len(source):]
                    files[name]=b;restores[name]={'source489_ZIP':n,'SHA256':sha(b)}
        for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:files[active+n]=z.read(before+n)
    files[active+'sd2snes/firmware.stm']=fw;files[active+'sd2snes/fpga_mmc492.bi3']=fpga
    files[active+'NES MMC3 492.nh1']=b''
    files[active+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=b'Copy original mmc489.nes (or480/482/485) as mmc492.nes without byte changes.393232B,CRC32 5a04eed7.\n'
    files['읽어주세요.txt']=(ROOT/'docs/nes-mmc492-trial.ko.md').read_bytes()
    files['verification.json']=(ROOT/'analysis/schedule492-verification.json').read_bytes()
    assert restores and not any(n.startswith(active)and n.lower().endswith('.nes')for n in files)
    assert not any(n.lower().endswith(('.srm','.sav','.rtc'))for n in files)
    assert {n for n in files if n.lower().endswith('.nes')}=={'05-RESTORE476-SD-ROOT/sd2snes/nes/nrom476.nes','07-RESTORE467-SD-ROOT/sd2snes/nes/nrom16.nes'}
    r={'passed':True,'candidate':'MMC492','limited_functional_trial_ready':True,'public_release':False,
       'hardware_verified':False,'physical_FPS':None,'physical_acceleration_verified':False,
       'client_ABI':'4891','profile_hex':'7b','status_version':3,'SMB3_ROM_included':False,
       'firmware_SHA256':sha(fw),'FPGA_SHA256':sha(fpga),'baseline489_ZIP_SHA256':old['ZIP_SHA256'],
       'verification_SHA256':sha(files['verification.json']),
       'required_ROM':{'path':'sd2snes/nes/mmc492.nes','bytes':393232,'CRC32':'5a04eed7','SHA256':'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'},
       'restores_byte_preserved':restores,'files':{n:{'bytes':len(b),'SHA256':sha(b)}for n,b in files.items()}}
    files['manifest.json']=(json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC492-SCHEDULE.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
        for n,b in files.items():z.writestr(n,b)
    with zipfile.ZipFile(archive)as z:assert z.testzip()is None and set(z.namelist())==set(files)and all(z.read(n)==b for n,b in files.items())
    r.update(ZIP_name=archive.name,ZIP_bytes=archive.stat().st_size,ZIP_SHA256=sha(archive.read_bytes()))
    (a.out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:r[k]for k in ['passed','ZIP_name','ZIP_bytes','ZIP_SHA256']}))
