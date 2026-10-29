# SPDX-License-Identifier: MIT
"""Package verified476 ARM with exact474 FPGA/ROM and byte-preserved restores."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--arm',type=Path,required=True)
parser.add_argument('--prior',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
r=json.loads((ROOT/'analysis/receive476-verification.json').read_text(encoding='utf8'))
old=json.loads((ROOT/'analysis/nrom474-package.json').read_text(encoding='utf8'))
assert r['passed'] and r['native_validation']['passed'] and r['live_validation']['passed']
assert all(x['passed'] and x['failed_state_frozen'] for x in r['M4_fault_validation'].values())
assert sha(args.prior)==old['zip_sha256']
fw=(args.arm/'obj-nes-100/firmware.stm').read_bytes()
assert hashlib.sha256(fw).hexdigest()==r['artifacts']['firmware_stm']
for s in [b'/sd2snes/nes/nrom476.nes',b'/sd2snes/fpga_nrom476.bi3',b'nes-progress-nrom476.txt',b'nes-budget-nrom476.txt',b'nes-game-last-nrom476.txt',b'cost_schema=474']:assert s in fw,s
files={}
roots={'02-RESTORE471-SD-ROOT/':'03-RESTORE471-SD-ROOT/',
       '03-STATIC-COMPARE-SD-ROOT/':'04-STATIC-COMPARE-SD-ROOT/',
       '04-RESTORE164-SD-ROOT/':'05-RESTORE164-SD-ROOT/',
       '05-RESTORE467-SD-ROOT/':'06-RESTORE467-SD-ROOT/'}
with zipfile.ZipFile(args.prior) as prior:
 for name in prior.namelist():
  data=prior.read(name)
  if name.startswith('01-NROM474-MOVING-SD-ROOT/'):
   files[name.replace('01-NROM474-MOVING-SD-ROOT/','02-RESTORE474-SD-ROOT/',1)]=data
   target=name.replace('01-NROM474-MOVING-SD-ROOT/','01-NROM476-MOVING-SD-ROOT/',1).replace('nrom474','nrom476').replace('NROM 474','NROM 476')
   files[target]=fw if name.endswith('/firmware.stm') else data
  else:
   for source,dest in roots.items():
    if name.startswith(source):
     target=name.replace(source,dest,1)
     if source.startswith('03-'):target=target.replace('nrom474','nrom476').replace('NROM 474','NROM 476')
     files[target]=data
moving=files['01-NROM476-MOVING-SD-ROOT/sd2snes/nes/nrom476.nes']
image=files['01-NROM476-MOVING-SD-ROOT/sd2snes/fpga_nrom476.bi3']
assert hashlib.sha256(moving).hexdigest()==r['artifacts']['moving_ROM']
assert hashlib.sha256(image).hexdigest()==r['artifacts']['FPGA_BI3']
for label,name in [('읽어주세요.txt','docs/nes-receive476-trial.ko.md'),('기술검증.txt','docs/nes-receive476-contract.ko.md'),('verification.json','analysis/receive476-verification.json')]:files[label]=(ROOT/name).read_bytes()
manifest={'trial':'NROM476','cost_schema':474,'paired_FPGA':'byte-identical471 renamed476','input_header':'2232','output_client':'2271','moving_scene_crc32_hex':f'{zlib.crc32(moving):08x}','physical476_fps':None,'physical474_baseline_fps':r['physical_baseline_FPS'],'firmware_sha256':hashlib.sha256(fw).hexdigest(),'FPGA_sha256':hashlib.sha256(image).hexdigest(),'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in files.items()}}
files['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
archive=args.out/'NROM476-RECEIVE.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name,data in files.items():z.writestr(name,data)
with zipfile.ZipFile(archive) as z:assert set(z.namelist())==set(files) and all(z.read(n)==v for n,v in files.items())
report={'passed':True,'zip_name':archive.name,'zip_bytes':archive.stat().st_size,'zip_sha256':sha(archive),'manifest':manifest}
(args.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:report[k] for k in ['zip_name','zip_bytes','zip_sha256']}))
