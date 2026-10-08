# SPDX-License-Identifier: MIT
"""Verify actual084 ARM has the pre-SD marker order and unchanged native IO."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_report084_prepare import sha,ROOT
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','objdump']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'source/src';o=s/'obj-report079'
 dis=subprocess.check_output([str(a.objdump),'-d',str(o/'sd2snes.elf')]).decode().replace('\r\n','\n')
 (a.arm/'disassembly.txt').write_text(dis,encoding='utf-8')
 fs=dict(re.findall(r'^[0-9a-f]+ <([^>]+)>:\n(.*?)(?=^[0-9a-f]+ <|\Z)',dis,re.M|re.S));edges={}
 for parent,child,count in [('main','sdreport_run084',1),('sdreport_run084','report_session084',1),
  ('report_session084','report_boot080',1),('report_session084','marker084',3),('report_session084','report_space084',1),('report_space084','get_fat',1),
  ('marker084','report_line080',1),('marker084','nes_return_delay',1),
  ('report_session084','sdn_report_initialize081',1),('report_session084','file_init',1),
  ('file_init','f_mount',1),('find_volume','disk_initialize',1),('disk_initialize','sdn_report_mounted081',1),
  ('report_session084','sdinv_write_report',1),('write_report','sdinv_checkpoint079',7),
  ('report_boot080','report_decode080',2),('report_half081','nes_return_delay',1)]:
  n=len(re.findall(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <'+child+r'>',fs[parent]));assert n==count,(parent,child,n)
  edges[parent+' -> '+child]=n
 body=fs['report_session084'];calls=re.findall(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <([^>]+)>',body)
 order=[n for n in calls if n in ['report_boot080','marker084','sdn_report_initialize081','file_init','report_space084','sdinv_write_report']]
 assert order==['report_boot080','marker084','sdn_report_initialize081','marker084','file_init','marker084','report_space084','sdinv_write_report'],order
 assert '<file_init>' not in fs['main'] and '<sdn_report_initialize081>' not in fs['main']
 for name in ['sdn_initialize','cmd_slow','acmd_slow','printf','nes_return_reset','nes_return_log_allow']:
  assert '<'+name+'>' not in fs['marker084'],name
 prep=json.loads((a.arm/'preparation084.json').read_bytes());prefix='work/arm-02/source/src/'
 same=['ff.c','fileops.c','stm32f4xx/timer.c','stm32f4xx/sdnative.c','stm32f4xx/nes_report_init081.inc',
       'fpga_spi.c','fpga.c','memory.c','nes_menu_return.c','nes_diag_runtime.c','snes.c',
       'nes_report_decode080.c','nes_report_disk081.c']
 for n in same:assert sha(s/n)==prep['inputs'][prefix+n],n
 assert sha(s/'nes_report_platform084.c')==sha(ROOT/'src/nes/firmware/nes_report_platform084.c')
 for n in ['nes_report_platform084.c','nes_report_space084.c','nes_report_layout084.h']:
  assert sha(s/n)==sha(ROOT/'src/nes/firmware'/n),n
 for name in ['nes_return_io_begin','nes_return_log_allow','put_fat','disk_write','f_write','nes_return_reset']:
  assert '<'+name+'>' not in fs['report_space084'],name
 fw=o/'firmware.stm';raw=fw.read_bytes()
 for marker in [b'SDREPORT084',b'STEP 1A INIT SD',b'STEP 1B MOUNT FAT',b'STEP 1C FIND SPACE',b'/HW084']:assert marker in raw,marker
 result=dict(edges=edges,order=order,firmware_bytes=len(raw),firmware_sha256=sha(fw),elf_sha256=sha(o/'sd2snes.elf'),unchanged_inputs=same,arm_executed=False,hardware_verified=False)
 (a.arm/'arm-check084.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
