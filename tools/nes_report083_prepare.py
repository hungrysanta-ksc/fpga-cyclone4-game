# SPDX-License-Identifier: MIT
"""Prepare SD-free observation before the exact081 native initialization."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
PIN='4e74c45d85315546c7d61c7f613ed4386283eb24c05c5724b506358e3381b757'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence081','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence081.resolve();out=a.out.resolve()
 assert not out.exists() and not out.is_relative_to(e)
 assert sha(e/'manifest.json')==PIN
 pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={};prefix='work/arm-02/source/'
 for k,h in pins.items():
  if not k.startswith(prefix):continue
  n=Path(k[len(prefix):])
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in n.parts):continue
  if n.suffix.lower() in ['.exe','.elf','.stm','.sof','.rbf','.o','.d','.lst','.map']:continue
  assert sha(e/k)==h,k
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/k,d);inputs[k]=h
 s=out/'src'
 shutil.copy2(ROOT/'src/nes/firmware/nes_report_platform083.c',s/'nes_report_platform083.c')
 for n,old,new,count in [('main.c','sdreport_run081','sdreport_run083',2),
                        ('Makefile','nes_report_platform081.c','nes_report_platform083.c',1),
                        ('nes_sd_inventory_log.c','/HW081','/HW083',1)]:
  f=s/n;text=f.read_text();assert text.count(old)==count
  f.write_text(text.replace(old,new),encoding='utf-8',newline='\n')
 (s/'VERSION').write_bytes(b'RELEASE_VERSION = "SDREPORT083"\r\n')
 record=dict(inputs=inputs,installable=False,files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
 (out.parent/'preparation083.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
 print('Prepared083 from pinned081 inputs='+str(len(inputs)))
if __name__=='__main__':main()
