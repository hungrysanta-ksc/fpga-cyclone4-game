# SPDX-License-Identifier: MIT
"""Final080 ELF and unchanged079 native input checks, not MCU execution."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--objdump',type=Path,required=True);a=p.parse_args();s=a.arm/'source/src';o=s/'obj-report079'
 dis=subprocess.check_output([str(a.objdump),'-d',str(o/'sd2snes.elf')]).decode().replace('\r\n','\n');(a.arm/'disassembly.txt').write_text(dis,encoding='utf-8')
 functions=dict(re.findall(r'^[0-9a-f]+ <([^>]+)>:\n(.*?)(?=^[0-9a-f]+ <|\Z)',dis,re.M|re.S));edges={}
 for parent,child,count in [('main','sdreport_run080',1),('sdreport_run080','report_session080',1),('report_session080','report_boot080',1),('report_boot080','report_decode080',2),('report_session080','report_line080',5),('report_session080','sdinv_write_report',1),('write_report','sdinv_checkpoint079',7)]:
  n=len(re.findall(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <'+child+r'>',functions[parent]));assert n==count,(parent,child,n);edges[parent+' -> '+child]=n
 for name in ['fpga_rompgm','load_bootrle','snes_bootclear','snes_bootprint_version','snes_bootprint_center','sleep_ms']:
  assert '<'+name+'>' not in functions['report_session080']+functions['report_boot080']
 assert '<file_init>' in functions['main'] # documented outstanding pre-scope mount
 prep=json.loads((a.arm/'preparation080.json').read_bytes());prefix='work/arm-03/source/src/'
 same=['ff.c','stm32f4xx/sdnative.c','stm32f4xx/timer.c','fpga_spi.c','fpga.c','memory.c','nes_menu_return.c','nes_diag_runtime.c','snes.c','nes_report_checkpoint079.c']
 for n in same:assert sha(s/n)==prep['inputs'][prefix+n],n
 for n in ['nes_report_boot080.h','nes_report_boot080.c','nes_report_decode080.c','nes_report_platform080.c']:assert sha(s/n)==sha(ROOT/'src/nes/firmware'/n),n
 fw=o/'firmware.stm';assert b'SDREPORT080' in fw.read_bytes()
 result=dict(edges=edges,firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(o/'sd2snes.elf'),unchanged_native=same,arm_executed=False,installable=False)
 (a.arm/'arm-check080.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
