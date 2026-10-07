# SPDX-License-Identifier: MIT
"""Audit frozen065 files, linked callers and reused trace boundary; no new run."""
from pathlib import Path
import argparse,json,re,tempfile
from nes_mcu_loader import FW,sha
from nes_menu_return import materialize
from nes_diag_recovery_checks import function

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence.resolve();m=read(e/'manifest.json')
 assert m['candidate']=='NES-MENU-RETURN-065'
 for n,h in m['files'].items():
  f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
 unit=e/'unit-07';u=read(unit/'result.json');assert not u['mutation']
 for n,count in [('copy',20),('wait',12),('log',24),('sd',16),('fatfs',7),('finish',14)]:
  assert u['results'][n]['exit_code']==0 and 'cases='+str(count) in u['results'][n]['last_line'],n
 for n in ['nes_menu_return.c','nes_menu_return.h','nes_return_spi.inc','nes_return_timer.inc','nes_return_sd_write.inc']:assert sha(unit/n)==sha(FW/n),n
 for kind in ['menu-compare','log-release','sd-crc','fatfs-budget']:
  r=read(e/('mutation-'+kind+'-03/result.json'));assert r['mutation']==kind and next(iter(r['results'].values()))['exit_code']!=0
 arm=e/'arm-06';prep=read(arm/'menu-return-preparation.json');assert not prep['installable']
 for n,h in prep['files'].items():assert sha(arm/'src'/n)==h,n
 for n in ['nes_menu_return.c','nes_menu_return.h','nes_menu_diagnostic.c','nes_h1_stm32.c','nes_diag_runtime.c','nes_diag_runtime.h']:
  for host in ['unit-07','menu-host-04','session-host-03']:assert sha(e/host/n)==sha(arm/'src'/n),(host,n)
 with tempfile.TemporaryDirectory() as temp:
  materialize(Path(temp))
  for n in ['nes_menu_return.c','nes_menu_diagnostic.c','nes_h1_stm32.c','nes_diag_runtime.h']:assert sha(Path(temp)/n)==sha(arm/'src'/n),n
 sd=(arm/'src/stm32f4xx/sdnative.c').read_text();ff=(arm/'src/ff.c').read_text();main=(arm/'src/main.c').read_text()
 assert (unit/'sd-write-functions.inc').read_text()==''.join(function(sd,n) for n in ['wait_busy','send_datablock'])
 assert (unit/'fatfs-cache-functions.inc').read_text()==''.join(function(ff,n) for n in ['move_window','get_fat','put_fat','create_chain'])
 assert (unit/'main-finish.inc').read_text() in main
 for n,file in [('nes_return_spi.inc','stm32f4xx/spi.c'),('nes_return_timer.inc','stm32f4xx/timer.c'),('nes_return_sd_write.inc','stm32f4xx/sdnative.c')]:assert (unit/n).read_text() in (arm/'src'/file).read_text(),n
 menu=read(e/'menu-host-04/result.json');assert 'PASS MENU065 regression=41 input_rejections=18 menu_sessions=16 no_START=1' in menu['markers']
 assert 'native_error_protection=2' in (e/'menu-host-04/host.log').read_text()
 session=read(e/'session-host-03/result.json');reference=read(e/'reused063.json');assert session['session'] and session['reference_identical'] and session['traces']==reference['host']['traces']
 for n,h in session['traces'].items():assert sha(e/'session-host-03'/(n+'.trace'))==h
 log=(e/'arm-08.log').read_text(encoding='utf-8-sig');assert 'PASS065 manual ELF markers=3 run_calls=1 shared_branches=2' in log and 'PASS: compile-only NES065' in log
 for f,name in [('memory-disassembly.txt','nes_return_copy_menu'),('fat-get-disassembly.txt','nes_return_io_step'),('fat-window-disassembly.txt','nes_return_io_step')]:assert re.search(r'\bbl\s+[^\r\n]*<'+name+'>',(arm/f).read_text(encoding='utf-8-sig')),f
 assert sha(arm/'firmware-nes-065-compile-only.stm')=='aa5bec7d945ed6904961e555f4c54599203aa32f764e2690bacca16127d7e5a5'
 print(f'PASS065 frozen files={len(m["files"])} helpers=93 mutations=4 menu=16 SPI063 identical ARM calls; no physical execution')
if __name__=='__main__':main()
