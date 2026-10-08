# SPDX-License-Identifier: MIT
"""Prepare SD-free observation before the exact081 native initialization."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
PIN='4e74c45d85315546c7d61c7f613ed4386283eb24c05c5724b506358e3381b757'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def apply084(s):
 for n in ['nes_report_space084.c','nes_report_layout084.h']:
  shutil.copy2(ROOT/'src/nes/firmware'/n,s/n)
 for n in ['nes_report_boot080.c','nes_report_checkpoint079.c']:
  f=s/n;t=f.read_text();t=t.replace('#include <string.h>','#include <string.h>\n#include "nes_report_layout084.h"')
  if n=='nes_report_boot080.c':
   old=" memset(data,' ',32);data[32]=0;memcpy(data,text,strlen(text));"
   new=' if(!report_format084(data,text))return fail(NES_DIAG_MENU);'
  else:
   old=" memset(line,' ',32); line[32]=0;\n memcpy(line,labels[stage-2],strlen(labels[stage-2]));"
   new=' if(!report_format084(line,labels[stage-2]))goto fail;'
  assert t.count(old)==1,n
  f.write_text(t.replace(old,new),encoding='utf-8',newline='\n')

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
 s=out/'src';apply084(s)
 shutil.copy2(ROOT/'src/nes/firmware/nes_report_platform084.c',s/'nes_report_platform084.c')
 for n,old,new,count in [('main.c','sdreport_run081','sdreport_run084',2),
                        ('Makefile','nes_report_platform081.c','nes_report_platform084.c nes_report_space084.c',1),
                        ('nes_sd_inventory_log.c','/HW081','/HW084',1)]:
  f=s/n;text=f.read_text();assert text.count(old)==count
  f.write_text(text.replace(old,new),encoding='utf-8',newline='\n')
 (s/'VERSION').write_bytes(b'RELEASE_VERSION = "SDREPORT084"\r\n')
 record=dict(inputs=inputs,installable=False,files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
 (out.parent/'preparation084.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
 print('Prepared084 from pinned081 inputs='+str(len(inputs)))
if __name__=='__main__':main()
