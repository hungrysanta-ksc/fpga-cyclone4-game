# SPDX-License-Identifier: MIT
"""Limited MMC509 trial; unchanged base/menu, no ROM/save/RESTORE payload."""
import argparse,json,zipfile
from pathlib import Path
from nes_schedule492 import sha
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['arm','assembly','prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();v=read(ROOT/'analysis/service509-release.json');old=read(ROOT/'analysis/capture502-package.json')
 assert v['passed']and v['limited_functional_trial_ready']and not v['hardware_verified']
 assert sha(a.prior)==old['ZIP_SHA256']
 fw=a.arm/'obj-nes-100/firmware.stm';fpga=a.assembly/'fpga_mmc509.bi3'
 assert sha(fw)==v['firmware_SHA256']and sha(fpga)==v['assembly']['BI3_SHA256']
 active='01-MMC509-SD-ROOT/';files={}
 with zipfile.ZipFile(a.prior)as z:
  assert z.testzip()is None
  for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:
   prior='01-MMC502-SD-ROOT/'+n;b=z.read(prior)
   import hashlib
   assert hashlib.sha256(b).hexdigest()==old['files'][prior]['SHA256']
   files[active+n]=b
 files[active+'sd2snes/firmware.stm']=fw.read_bytes();files[active+'sd2snes/fpga_mmc509.bi3']=fpga.read_bytes();files[active+'NES MMC3 509.nh1']=b''
 files[active+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=b'Copy your original mmc502.nes to mmc509.nes without changing bytes.393232 bytes,CRC32 5a04eed7.\n'
 files['읽어주세요.txt']=(ROOT/'docs/nes-mmc509-trial.ko.md').read_bytes()
 files['verification.json']=(ROOT/'analysis/service509-release.json').read_bytes()
 assert not any('RESTORE'in n or n.lower().endswith(('.nes','.sav','.srm','.rtc'))for n in files)
 import hashlib
 r=dict(passed=True,candidate='MMC509',hardware_verified=False,physical_FPS=None,ROM_included=False,RESTORE_included=False,firmware_SHA256=sha(fw),FPGA_SHA256=sha(fpga),baseline502_ZIP_SHA256=sha(a.prior),required_ROM={**old['required_ROM'],'path':'sd2snes/nes/mmc509.nes'},logs=['sd2snes/nes-'+n+'-mmc509.txt'for n in ['progress','budget','game-last']],files={n:dict(bytes=len(b),SHA256=hashlib.sha256(b).hexdigest())for n,b in files.items()})
 files['manifest.json']=(json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC509-OVERLAP.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for n,b in files.items():z.writestr(n,b)
 with zipfile.ZipFile(archive)as z:assert z.testzip()is None and set(z.namelist())==set(files)and all(z.read(n)==b for n,b in files.items())
 r.update(ZIP_name=archive.name,ZIP_bytes=archive.stat().st_size,ZIP_SHA256=sha(archive))
 (a.out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:r[k]for k in ['passed','ZIP_name','ZIP_bytes','ZIP_SHA256']}))
