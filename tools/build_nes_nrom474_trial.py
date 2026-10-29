# SPDX-License-Identifier: MIT
"""Package validated474 ARM with exact471 FPGA and same moving/static NROMs."""
import argparse,hashlib,json,zipfile,zlib
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
r=json.loads((ROOT/'analysis/nrom474-verification.json').read_text(encoding='utf8'));assert r['passed']
old=BASE/'probes/nes-nrom471/trial03/NROM471-COST-PROBE.zip';spec=json.loads((ROOT/'analysis/nrom471-package.json').read_text(encoding='utf8'));assert sha(old)==spec['zip_sha256']
fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes();assert hashlib.sha256(fw).hexdigest()==r['artifacts']['firmware_stm']
for text in [b'/sd2snes/nes/nrom474.nes',b'/sd2snes/fpga_nrom474.bi3',b'nes-progress-nrom474.txt',b'nes-budget-nrom474.txt',b'nes-game-last-nrom474.txt',b'cost_schema=474']:assert text in fw,text
files={}
with zipfile.ZipFile(old) as z:
 for n in z.namelist():
  if n.startswith('01-NROM471-MOVING-SD-ROOT/'):
   v=z.read(n);files[n.replace('01-NROM471-MOVING-SD-ROOT/','02-RESTORE471-SD-ROOT/',1)]=v
   target=n.replace('01-NROM471-MOVING-SD-ROOT/','01-NROM474-MOVING-SD-ROOT/',1).replace('nrom471','nrom474').replace('NROM 471','NROM 474')
   files[target]=fw if n.endswith('/firmware.stm') else v
  elif n.startswith('03-STATIC-COMPARE-SD-ROOT/'):
   files[n.replace('nrom471','nrom474')]=z.read(n)
  elif n.startswith('04-RESTORE164-SD-ROOT/'):files[n]=z.read(n)
  elif n.startswith('02-RESTORE467-SD-ROOT/'):files[n.replace('02-RESTORE467-SD-ROOT/','05-RESTORE467-SD-ROOT/',1)]=z.read(n)
moving=files['01-NROM474-MOVING-SD-ROOT/sd2snes/nes/nrom474.nes'];image=files['01-NROM474-MOVING-SD-ROOT/sd2snes/fpga_nrom474.bi3']
assert hashlib.sha256(moving).hexdigest()==r['artifacts']['moving_ROM'];assert hashlib.sha256(image).hexdigest()==r['artifacts']['FPGA_BI3']
for label,path in [('읽어주세요.txt','docs/nes-nrom474-trial.ko.md'),('기술검증.txt','docs/nes-nrom474-contract.ko.md'),('verification.json','analysis/nrom474-verification.json')]:files[label]=(ROOT/path).read_bytes()
m={'trial':'NROM474','paired_FPGA':'byte-identical471 renamed fpga_nrom474.bi3','input_header':'2232','output_client':'2271','moving_scene_crc32_hex':f'{zlib.crc32(moving):08x}','firmware_sha256':hashlib.sha256(fw).hexdigest(),'FPGA_sha256':hashlib.sha256(image).hexdigest(),'physical474_fps':None,'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in files.items()}}
files['manifest.json']=(json.dumps(m,indent=2,ensure_ascii=False)+'\n').encode('utf8');out=a.out/'NROM474-PLANNER-POLL.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for n,v in files.items():z.writestr(n,v)
with zipfile.ZipFile(out) as z:assert set(z.namelist())==set(files) and all(z.read(n)==v for n,v in files.items())
report={'passed':True,'zip':str(out),'zip_bytes':out.stat().st_size,'zip_sha256':sha(out),'manifest':m}
(a.out/'result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print(json.dumps({'zip':str(out),'bytes':out.stat().st_size,'sha256':sha(out)}))
