# SPDX-License-Identifier: MIT
"""Audit frozen064 evidence; not a new execution or public-only reproduction."""
from pathlib import Path
import argparse,json,re
from nes_mcu_loader import FW,sha
from nes_diag_recovery import source
from nes_diag_recovery_checks import function

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence.resolve()
 m=read(e/'manifest.json');assert m['candidate']=='NES-DIAG-RECOVERY-064'
 for n,h in m['files'].items():
  f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
 u=read(e/'unit-09/result.json');assert not u['mutation']
 for n,count in [('fpga',22),('sd',24),('led',16),('uart',5),('fatfs',6)]:
  r=u['results'][n];assert r['exit_code']==0 and ('cases='+str(count)) in r['marker'],n
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h','nes_diag_platform.c','nes_diag_fpga.inc','nes_diag_sd.inc']:assert sha(e/'unit-09'/n)==sha(FW/n),n
 for kind in ['sd-success','fpga-done']:
  r=read(e/('mutation-'+kind+'-02/result.json'));assert r['mutation']==kind
  assert next(iter(r['results'].values()))['exit_code']!=0
 menu=read(e/'menu-host-04/result.json');assert 'PASS MENU064 regression=41 input_rejections=18 menu_sessions=16 no_START=1' in menu['markers']
 assert 'PASS RECOVERY064 native_error_protection=2 no_SD_base_retry=1' in (e/'menu-host-04/host.log').read_text()
 session=read(e/'session-host-03/result.json');assert session['session'] and session['reference_identical']
 reference=read(e/'reused063.json');assert session['traces']==reference['host']['traces']
 for case in ['fine_x','banks32']:assert sha(e/'session-host-03'/(case+'.trace'))==session['traces'][case]
 arm=e/'arm-06';prep=read(arm/'diag-recovery-preparation.json');assert not prep['installable']
 for n,h in prep['files'].items():assert sha(arm/'src'/n)==h,n
 for f in ['menu-host-04','session-host-03']:
  assert (e/f/'nes_h1_stm32.c').read_text()==source()
  for n in ['nes_h1_stm32.c','nes_menu_diagnostic.c','nes_menu_diagnostic.h','nes_diag_runtime.c','nes_diag_runtime.h']:assert sha(e/f/n)==sha(arm/'src'/n),n
 sd=(arm/'src/stm32f4xx/sdnative.c').read_text()
 assert (e/'unit-09/sd-command-functions.inc').read_text()==''.join(function(sd,n) for n in ['get_and_check_datacrc','wait_busy','send_command_fast'])
 assert (e/'unit-09/sd-read-function.inc').read_text()==function(sd,'sdn_read')
 uart=(arm/'src/stm32f4xx/uart.c').read_text();assert (e/'unit-09/uart-functions.inc').read_text()==function(uart,'uart_putc')+function(uart,'uart_flush')
 log=(arm/'build.log').read_text(encoding='utf-8-sig');assert 'PASS064 manual ELF markers=3 run_calls=1 shared_branches=2' in log and 'PASS: compile-only NES064' in log
 dump=(arm/'probe-disassembly.txt').read_text(encoding='utf-8-sig');assert len(re.findall(r'\bbl\s+[^\r\n]*<nes_diag_fpga_pgm>',dump))==2
 assert '<nes_diag_sd_failed>' in dump and '<nes_diag_begin>' in dump and '<nes_diag_leave>' in dump
 print(f'PASS064 frozen files={len(m["files"])}; lower helpers/FatFS/menu/identical SPI/ARM calls; no physical execution')
if __name__=='__main__':main()
