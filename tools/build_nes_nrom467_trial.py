# SPDX-License-Identifier: MIT
"""Build offline limited hardware trial with paired artifacts and restore files."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from nes_delta231 import BASE,ROOT
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
spec=json.loads((ROOT/'analysis/nrom465-entry.json').read_text());files={}
for name,path in {'sd2snes/firmware.stm':BASE/'probes/nes-nrom418/arm01/src/obj-nes-100/firmware.stm','sd2snes/fpga_nrom16.bi3':BASE/'probes/nes-nrom458/asm01/fpga_nrom16.bi3','sd2snes/nes/nrom16.nes':BASE/'probes/nes-nrom428/fixture01/nrom16.nes'}.items():files['01-NROM-SD-ROOT/'+name]=path.read_bytes()
with zipfile.ZipFile(BASE/'probes/nes-repeat227/release01/NES227-SMB3-OAMREPEAT.zip') as z:
 for name in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:files['01-NROM-SD-ROOT/'+name]=z.read('01-GAME227-SD-ROOT/'+name)
 for name in ['sd2snes/firmware.stm','sd2snes/fpga_n164.bi3','sd2snes/fpga_base.bi3','sd2snes/m3nu.bin','NES GAME 164.nh1']:
  data=z.read('02-RESTORE164-SD-ROOT/'+name);assert hashlib.sha256(data).hexdigest()==json.loads((ROOT/'analysis/release227-verification.json').read_text())['preserved']['02-RESTORE164-SD-ROOT/'+name];files['02-RESTORE164-SD-ROOT/'+name]=data
files['01-NROM-SD-ROOT/NES GAME 227.nh1']=b''
for name,v in spec['expected_files'].items():assert hashlib.sha256(files['01-NROM-SD-ROOT/'+name]).hexdigest()==v['sha256']
files['읽어주세요.txt']=(ROOT/'docs/nes-nrom467-trial.ko.md').read_bytes()
manifest={'kind':'limited experimental NROM16 hardware trial','FPGA_candidate':457,'ARM':418,'fixture':428,'new_candidate466_selected':False,'full_timing_signoff':False,'physical_test_completed':False,'fps60_proven':False,'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()}}
files['manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
path=a.out/'NROM467-LIMITED-TRIAL.zip'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 for name,data in files.items():z.writestr(name,data)
with zipfile.ZipFile(path) as z:
 assert set(z.namelist())==set(files) and all(z.read(n)==b for n,b in files.items())
r={'passed':True,'zip_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'zip_bytes':path.stat().st_size,'manifest':manifest,'scope':'offline paired artifacts and restore packaging; user installs and observes hardware; unresolved IO/CDC limits remain'}
(a.out/'result.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print(json.dumps({'zip':str(path),'bytes':r['zip_bytes'],'sha256':r['zip_sha256']}))
