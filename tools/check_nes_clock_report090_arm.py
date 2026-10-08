# SPDX-License-Identifier: MIT
"""Inspect linked090 ARM call sites and exact host/ARM/payload inputs."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_report084_prepare import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','host','evidence089','objdump']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'source/src';o=s/'obj-report079'
 dis=subprocess.check_output([str(a.objdump.resolve()),'-d',str(o/'sd2snes.elf')]).decode().replace('\r\n','\n')
 (a.arm/'disassembly.txt').write_text(dis,encoding='utf-8')
 fs=dict(re.findall(r'^[0-9a-f]+ <([^>]+)>:\n(.*?)(?=^[0-9a-f]+ <|\Z)',dis,re.M|re.S));edges={}
 required=[('main','sdreport_run090',1),('sdreport_run090','report_session090',1),('report_session090','report_boot080',2),('report_session090','marker090',4),('report_session090','nes_clock_config089',1),('report_session090','nes_clock_collect088',1),('report_session090','clock_text090',1),('report_session090','sdn_report_initialize081',1),('report_session090','file_init',1),('report_session090','report_space084',1),('report_session090','sdinv_write_report',1),('report_session090','nes_return_reset',1),('report_session090','nes_return_io_begin',1),('file_init','f_mount',1),('find_volume','disk_initialize',1),('disk_initialize','sdn_report_mounted081',1),('write_report','sdinv_checkpoint079',7),('report_boot080','report_decode080',2),('report_half081','nes_return_delay',1)]
 for parent,child,count in required:
  n=len(re.findall(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <'+child+r'>',fs[parent]));assert n==count,(parent,child,n);edges[parent+' -> '+child]=n
 wanted=['report_boot080','marker090','nes_clock_config089','nes_clock_collect088','clock_text090','sdn_report_initialize081','file_init','report_space084','sdinv_write_report']
 calls=re.findall(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <([^>]+)>',fs['report_session090']);order=[n for n in calls if n in wanted]
 assert order==['report_boot080','marker090','nes_clock_config089','nes_clock_collect088','clock_text090','report_boot080','marker090','sdn_report_initialize081','marker090','file_init','marker090','report_space084','sdinv_write_report'],order
 for parent in ['marker090','nes_clock_config089','nes_clock_collect088']:
  for child in ['nes_return_reset','nes_return_io_begin','nes_return_log_allow','printf']:
   assert '<'+child+'>' not in fs[parent],(parent,child)
 assert '<file_init>' not in fs['main'] and '<sdn_report_initialize081>' not in fs['main']
 prep=json.loads((a.arm/'preparation090.json').read_bytes());prefix='work/arm-01/source/src/'
 same=['ff.c','fileops.c','stm32f4xx/timer.c','stm32f4xx/sdnative.c','stm32f4xx/nes_report_init081.inc','fpga_spi.c','fpga.c','memory.c','nes_menu_return.c','nes_diag_runtime.c','snes.c','nes_report_decode080.c','nes_report_disk081.c']
 for n in same:assert sha(s/n)==prep['inputs'][prefix+n],n
 host_same=['nes_clock_config089.c','nes_clock_reader088.c','nes_clock_platform090.c','nes_clock_text090.c','nes_diag_runtime.c','nes_sd_inventory_log.c','nes_report_checkpoint079.c','nes_report_disk081.c','nes_report_boot080.c','nes_report_decode080.c','nes_report_space084.c']
 for n in host_same:assert sha(s/n)==sha(a.host/n),n
 # The084 host keeps the exact runtime prefix; unrelated menu-copy is absent.
 menu=(s/'nes_menu_return.c').read_text();assert menu[:menu.index('uint32_t nes_return_copy_menu(')]==(a.host/'nes_menu_return.c').read_text()
 raw=(o/'firmware.stm').read_bytes();rle=(a.evidence089/'asm01/clock087.rle').read_bytes();assert raw.count(rle)==1
 for marker in [b'CLOCKREPORT090',b'STEP 1A OBSERVE CLOCK',b'STEP 1B INIT SD',b'STEP 1C MOUNT FAT',b'STEP 1D FIND SPACE',b'/HW090',b'CAPTURED_WINDOWS:']:assert marker in raw,marker
 result=dict(edges=edges,order=order,unchanged_inputs=same,host_same=host_same,menu_runtime_prefix_exact=True,firmware_bytes=len(raw),firmware_sha256=sha(o/'firmware.stm'),elf_sha256=sha(o/'sd2snes.elf'),embedded_rle_sha256=sha(a.evidence089/'asm01/clock087.rle'),arm_executed=False,installable=False,hardware=False)
 (a.arm/'arm-check090.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
