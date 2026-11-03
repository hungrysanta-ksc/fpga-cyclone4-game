# SPDX-License-Identifier: MIT
"""Package the audited 576 FPGA and identical-code MMC577 labels; no ROM or RESTORE."""
import argparse,json,hashlib,zipfile
from pathlib import Path
from nes_raw506 import sha
from nes_cf68_pair_preflight import encode,decode
p=argparse.ArgumentParser()
for n in ('arm','board','image','prior','out'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();root=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
ev=root/'analysis/gate577-verification.json';r=read(ev)
# Historical manifest used the Windows CP949 default. Keep its bytes unchanged.
old=json.loads((root/'analysis/trial558-package.json').read_text(encoding='cp949'))
assert r['gate']=='limited physical trial only' and not r['physical_verified']
assert sha(a.arm/'obj-nes-100/firmware.stm')==r['firmware_SHA256']
assert sha(a.board/'output_files/board.sof')==r['board']['SOF']
assert sha(a.prior)==old['ZIP_SHA256']
rbf=(a.image/'board.rbf').read_bytes();bi3=(a.image/'fpga_mmc577.bi3').read_bytes()
assert decode(bi3)==rbf and encode(rbf)==bi3
assert sha(a.image/'board.rbf')==r['programmer']['rbf_sha256']
assert sha(a.image/'fpga_mmc577.bi3')==r['programmer']['image_sha256']
prefix='01-MMC577-SD-ROOT/';fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes()
marker='NES MMC3 577.nh1';rom='sd2snes/nes/mmc577.nes'
logs=[f'sd2snes/nes-{n}-mmc577.txt' for n in ['progress','budget','game-last']]
for path in [marker,'sd2snes/fpga_mmc577.bi3',rom,*logs]:
 assert (path if path==marker else '/'+path).encode()+b'\0' in fw
files={prefix+'sd2snes/firmware.stm':fw,prefix+'sd2snes/fpga_mmc577.bi3':bi3,prefix+marker:b'',
 prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt':b'Copy your own unchanged mmc558.nes to mmc577.nes. CRC32 5a04eed7.\n',
 'README-KO.txt':(root/'docs/nes-mmc577-trial.ko.md').read_bytes()}
with zipfile.ZipFile(a.prior) as z:
 for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:
  path='01-MMC558-SD-ROOT/'+n;data=z.read(path)
  assert hashlib.sha256(data).hexdigest()==old['files'][path]
  files[prefix+n]=data
assert not any('RESTORE' in n or n.lower().endswith(('.nes','.sav','.srm','.rtc')) for n in files)
result=dict(candidate='MMC577',physical_verified=False,gate=r['gate'],timing_policy=r['timing_policy'],
 firmware_SHA256=r['firmware_SHA256'],SOF_SHA256=r['board']['SOF'],RBF_SHA256=sha(a.image/'board.rbf'),
 BI3_SHA256=sha(a.image/'fpga_mmc577.bi3'),evidence_SHA256=sha(ev),
 required_ROM=dict(path=rom,CRC32='5a04eed7',sha256=old['compatible_ROM']),logs=logs,
 ROM_included=False,RESTORE_included=False,
 files={n:hashlib.sha256(data).hexdigest() for n,data in files.items()})
files['manifest.json']=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8')
a.out.mkdir(parents=True,exist_ok=False);out=a.out/'MMC577-TRIAL.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for n,data in files.items():z.writestr(n,data)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None and set(z.namelist())==set(files)
 for n,data in files.items():assert z.read(n)==data
result.update(ZIP_SHA256=sha(out),ZIP_bytes=out.stat().st_size)
(a.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
print(out,result['ZIP_SHA256'])
