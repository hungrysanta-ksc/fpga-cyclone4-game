# SPDX-License-Identifier: MIT
"""Materialize a new090 tree; never change frozen084/089 inputs."""
from pathlib import Path
import argparse,json,shutil
from nes_report084_prepare import sha,ROOT
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence084','evidence089','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence084.resolve();v=a.evidence089.resolve();out=a.out.resolve()
 assert not out.exists() and not out.is_relative_to(e) and not out.is_relative_to(v)
 assert sha(e/'manifest.json')=='1a43873e74e8a5cc888d099874d9ff17caa6959b4b12ffdd53a9d0987100a3d5'
 assert sha(v/'manifest.json')=='9f1a6a39c0b1d39b725d6f85a04653736ab77a06091986e398a85d1102914018'
 pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={};prefix='work/arm-01/source/'
 for k,h in pins.items():
  if not k.startswith(prefix):continue
  n=Path(k[len(prefix):])
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in n.parts):continue
  if n.suffix.lower() in ['.exe','.elf','.stm','.sof','.rbf','.o','.d','.lst','.map']:continue
  assert sha(e/k)==h,k
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/k,d);inputs[k]=h
 s=out/'src'
 names=['nes_clock_config089.c','nes_clock_config089.h','nes_clock_reader088.c','nes_clock_reader088.h','nes_clock_platform090.c','nes_clock_report090.h','nes_clock_text090.c']
 for n in names:shutil.copy2(ROOT/'src/nes/firmware'/n,s/n)
 h='asm01/clock089_payload.h';assert sha(v/h)==json.loads((v/'manifest.json').read_bytes())['files'][h];shutil.copy2(v/h,s/'clock089_payload.h')
 for n,old,new,count in [('main.c','sdreport_run084','sdreport_run090',2),('Makefile','nes_report_platform084.c','nes_clock_platform090.c nes_clock_text090.c nes_clock_config089.c nes_clock_reader088.c',1),('nes_sd_inventory_log.c','/HW084','/HW090',1)]:
  q=s/n;t=q.read_text();assert t.count(old)==count,(n,t.count(old));q.write_text(t.replace(old,new),encoding='utf-8',newline='\n')
 (s/'VERSION').write_bytes(b'RELEASE_VERSION = "CLOCKREPORT090"\r\n')
 result=dict(inputs=inputs,installable=False,files={q.relative_to(out).as_posix():sha(q) for q in out.rglob('*') if q.is_file()})
 (out.parent/'preparation090.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print('Prepared090 inputs='+str(len(inputs)))
if __name__=='__main__':main()
