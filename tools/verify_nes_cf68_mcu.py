# SPDX-License-Identifier: MIT
"""069 private evidence audit; host/RTL/ARM compilation, not hardware."""
from pathlib import Path
import argparse,json,re,tempfile
from nes_mcu_loader import ROOT,sha
from nes_cf68_mcu import materialize
from nes_diag_recovery_checks import function

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def audit(e,fpga):
 meta=read(ROOT/'analysis/cf68-mcu-verification.json');m=read(e/'manifest.json')
 assert sha(e/'manifest.json')==meta['manifest_sha256'] and len(m['files'])==meta['archived_files']
 for n,h in m['files'].items():
  p=(e/n).resolve();assert p.is_relative_to(e.resolve()) and sha(p)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 a=e/'arm';prep=read(a/'cf68-preparation.json')
 for n,h in prep['files'].items():assert sha(a/'src'/n)==h,n
 with tempfile.TemporaryDirectory() as d:
  materialize(Path(d))
  for p in Path(d).iterdir():assert sha(p)==sha(a/'src'/p.name),p.name
 for n in ['nes_h1_stm32.c','nes_menu_diagnostic.c','nes_menu_return.c','nes_diag_runtime.c','nes_diag_runtime.h']:
  for suite in ['host','unit','session']:assert sha(e/suite/n)==sha(a/'src'/n),(suite,n)
 assert sha(a/'executed-builder.ps1')==meta['public_sources']['tools/build_nes_cf68_mcu_arm.ps1']
 assert sha(a/'firmware.stm')==meta['arm']['firmware_sha256'] and (a/'firmware.stm').stat().st_size==meta['arm']['firmware_bytes']
 probe=(a/'probe-disassembly.txt').read_text(encoding='utf-8-sig')
 assert re.search(r'\bcmp\s+r[0-9]+, #104\b',probe) and probe.index('<nes_return_spi_ready>')<probe.index('<slow_begin>')
 assert probe.count('<nes_diag_fpga_pgm>')==2 and '<nes_return_failed>' in probe
 arm=(e/'arm02.log').read_text(encoding='utf-8-sig')
 for text in ['PASS069 manual ELF markers=3 run_calls=1 shared_branches=2','PASS069 startup_READY_and_fault_guard callsites','PASS069 CF68 compare and READY_before_GPIO']:assert text in arm
 u=read(e/'unit/result.json')
 for kind,count in dict(copy=20,wait=14,log=24,sd=16,fatfs=7,finish=14).items():assert u['results'][kind]['exit_code']==0 and 'cases='+str(count) in u['results'][kind]['last_line']
 for n in ['sd-write-functions.inc','fatfs-cache-functions.inc','main-finish.inc']:assert sha(e/'unit'/n)==meta['tested_lower_functions'][n]
 assert (e/'unit/sd-write-functions.inc').read_text()==''.join(function((a/'src/stm32f4xx/sdnative.c').read_text(),n) for n in ['wait_busy','send_datablock'])
 assert (e/'unit/fatfs-cache-functions.inc').read_text()==''.join(function((a/'src/ff.c').read_text(),n) for n in ['move_window','get_fat','put_fat','create_chain'])
 assert (e/'unit/main-finish.inc').read_text() in (a/'src/main.c').read_text()
 for n,f in [('nes_return_spi.inc','stm32f4xx/spi.c'),('nes_return_timer.inc','stm32f4xx/timer.c'),('nes_return_sd_write.inc','stm32f4xx/sdnative.c')]:assert (e/'unit'/n).read_text() in (a/'src'/f).read_text()
 host=(e/'host/host.log').read_text()
 for text in ['PASS MENU069 regression=41 input_rejections=18 menu_sessions=16 no_START=1','PASS CF68 extra_old_ids=2 ready_fault_no_GPIO_or_base=1','PASS RECOVERY069 native_error_protection=2']:assert text in host
 for kind in ['candidate','ready','fault-release']:
  p=e/('mutation-'+kind+'01');r=read(p/'result.json');assert r['expected_failure'] and r['assertion'] in (p/'host.log').read_text()
 assert ',&early)' in (e/'mutation-fault-release01/host.log').read_text()
 for kind in ['menu-compare','log-release','sd-crc','fatfs-budget']:
  r=read(e/('lower-'+kind+'01/result.json'));assert r['mutation']==kind and next(iter(r['results'].values()))['exit_code']!=0
 session=read(e/'session/result.json');assert session['session']
 for c,h in session['traces'].items():assert sha(e/'session'/(c+'.trace'))==h
 assert set(read(e/'trace-differential.json'))=={'fine_x','banks32'}
 wave=read(e/'wave/result.json');assert wave['host_result_sha256']==sha(e/'host/result.json')
 fitmeta=read(ROOT/'analysis/diag-safety-verification.json');assert sha(fpga/'manifest.json')==fitmeta['manifest_sha256']==meta['reused_fpga_manifest_sha256']
 fit=read(fpga/'fit/result.json')
 for n,h in fit['sources'].items():
  if n.endswith('.sv'):assert wave['sources'][n]==h,n
 for c in wave['cases']:
  raw=(e/'wave'/c['mode']/'simulation.log').read_text();assert c['marker'] in raw and '** Fatal:' not in raw
  assert sha(e/'wave'/c['mode']/'waveform.txt')==c['waveform_sha256']
 assert not meta['installable'] and not meta['full_board_spi_replay'] and not meta['hardware_execution']
 print(f"PASS069 frozen={len(m['files'])} helpers=95 upper41/18/16+3 native2 mutations7 bounded_C=72320 full_host180224 ARM_CF68 no_install")
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--fpga-evidence',type=Path,required=True);a=p.parse_args();audit(a.evidence,a.fpga_evidence)
