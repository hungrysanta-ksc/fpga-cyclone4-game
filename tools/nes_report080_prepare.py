# SPDX-License-Identifier: MIT
"""Add bounded embedded mini/boot and terminal screen to pinned079 candidate."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
PIN='81c3ff5b7af8911c27d0429ca25a6670b11f0dfd90dc0e6027b7b0ce17a95b13'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def array(p):return bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]{2})',p.read_text()))
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence079',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 e=a.evidence079.resolve();out=a.out.resolve();assert not out.exists() and not out.is_relative_to(e)
 assert sha(e/'manifest.json')==PIN;m=json.loads((e/'manifest.json').read_bytes())['files'];used={}
 prefix='work/arm-03/source/'
 for k,h in m.items():
  if not k.startswith(prefix):continue
  n=Path(k[len(prefix):])
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in n.parts):continue
  if n.suffix.lower() in ['.exe','.elf','.stm','.sof','.rbf','.o','.d','.lst','.map']:continue
  assert sha(e/k)==h;kout=out/n;kout.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/k,kout);used[k]=h
 src=out/'src'
 for name in ['nes_report_boot080.h','nes_report_boot080.c','nes_report_decode080.c','nes_report_platform080.c']:
  shutil.copy2(ROOT/'src/nes/firmware'/name,src/name)
 assert sha(out/'verilog/sd2snes_mini/fpga_mini.bi3')=='9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9'
 boot=array(src/'snesboot.h');assert len(boot)==2811 and hashlib.sha256(boot).hexdigest()=='4805e32bc1118c266e69d0424f503b55c7016d3b21d61bec03527a3f06a08ff5'
 f=src/'main.c';s=f.read_text();assert s.count('sdreport_run079')==2;f.write_text(s.replace('sdreport_run079','sdreport_run080'),encoding='utf-8',newline='\n')
 f=src/'Makefile';s=f.read_text();assert s.count('nes_report_platform079.c')==1;f.write_text(s.replace('nes_report_platform079.c','nes_report_platform080.c nes_report_boot080.c nes_report_decode080.c'),encoding='utf-8',newline='\n')
 f=src/'nes_sd_inventory_log.c';s=f.read_text();assert s.count('/HW079')==1;f.write_text(s.replace('/HW079','/HW080'),encoding='utf-8',newline='\n')
 (src/'VERSION').write_bytes(b'RELEASE_VERSION = "SDREPORT080"\r\n')
 record=dict(inputs=used,installable=False,files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
 (out.parent/'preparation080.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('Prepared080 from pinned079 inputs='+str(len(used)))
if __name__=='__main__':main()
