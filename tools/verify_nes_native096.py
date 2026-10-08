# SPDX-License-Identifier: MIT
"""Verify preserved native096 executions; does not execute hardware or tests."""
from pathlib import Path
import argparse,json,re
from nes_spi_boot import ROOT,sha
from nes_diag_recovery_checks import function

NORMAL={
 'suite05':(76,'fine_x',False,False,503),
 'fat32-96-02':(76,'banks32',True,True,603),
 'fat32-block80':(1,'fine_x',True,False,507),
 'fat16-byte96':(1,'banks32',False,True,599),
}
NEGATIVE={
 'negative-crc02':('sd-crc','!safe&&!r.sd.verified&&nes_cf86_failed094()&&!irq&&reset_held&&first_error096'),
 'negative-ready02':('ready-wait','safe&&r.sd.verified&&r.sd.load.stop_ok&&r.sd.load.base_restored&&configs==2&&irq&&reset_held&&finishes==1&&check_acks==original_length-16'),
 'negative-config01':('config-run','b==expected'),
 'negative-latch01':('failed-latch','card_commands096()==before_commands&&frames==before_frames&&configs==before_configs&&!irq&&reset_held'),
}
NATIVE=['nes_diag_sd_error','nes_diag_sd_reset','nes_diag_sd_failed','sdn_status',
 'wiggle_fast_pos','wiggle_fast_neg','wiggle_fast_neg1','wiggle_fast_pos1','get_and_check_datacrc',
 'wait_busy','send_command_fast','make_crc7','cmd_fast','send_datablock','nes_diag_sd_response',
 'nes_diag_sd_read','sdn_read','nes_return_sd_write','sdn_write','sdn_ioctl']

def verify_runs(e,prefix=''):
 latest=json.loads((ROOT/'analysis/session094-verification.json').read_bytes())
 ordinary=0
 for name in list(NORMAL)+list(NEGATIVE):
  d=e/(prefix+name);r=json.loads((d/'result.json').read_bytes())
  for n,h in r['files'].items():assert sha(d/n)==h,(name,n)
  assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_native096.py'),name
  for n in ['native096_bridge.h','native096_card.inc','native096_host.c']:
   assert sha(d/n)==sha(ROOT/'tests/nes-functional'/n)==r['inputs']['public/'+n],(name,n)
  for c in r['cases']:
   log=d/(c['name']+'.log');assert sha(log)==c['log_sha256'] and c['marker'] in log.read_text(),(name,c['name'])
  if name in NEGATIVE:
   mutation,expected=NEGATIVE[name]
   assert r['mutation']==mutation and r['expected_failure'] and len(r['cases'])==1
   assert 'Assertion failed: '+expected in (d/(r['cases'][0]['name']+'.log')).read_text(),name
   continue
  count,case,fat32,sdsc,commands=NORMAL[name]
  assert not r['mutation'] and not r['production_changed'] and not r['physical'] and r['actual_native_sd']
  assert (len(r['cases']),r['case'],r['fat32'],r['sdsc'])==(count,case,fat32,sdsc)
  for n,h in latest['host_arm_identical'].items():assert sha(d/n)==h,(name,n)
  for n,h in r['inputs'].items():
   if not n.startswith('arm04/src/'):continue
   short=n.removeprefix('arm04/src/')
   target={'ccsbcs.c':'unicode/ccsbcs.c','stm32f4xx/sdnative.c':'input-sdnative.c','fpga.c':'input-fpga.c','fpga_spi.h':'input-fpga_spi.h','stm32f4xx/spi.c':'input-spi.c'}.get(short,short)
   assert sha(d/target)==h,(name,n)
  raw=(d/'input-sdnative.c').read_text();bodies=[]
  for n in NATIVE:
   m=re.search(r'^(?:static inline void|static void|static bool|static DRESULT|int|void|bool|DRESULT|DSTATUS) '+n+r'\([^;{}]*\)\s*\{',raw,re.M);assert m,n
   bodies.append(function(raw[m.start():],n))
  assert (d/'native.inc').read_text()==''.join(bodies)
  raw=(d/'input-fpga.c').read_text();assert (d/'config.inc').read_text()==raw[raw.index('struct nes_diag_input {'):]
  raw=(d/'input-spi.c').read_text();assert (d/'ready.inc').read_text()==function(raw,'nes_return_spi_wait')+function(raw,'nes_return_spi_ready')
  total=81920 if case=='fine_x' else 98304
  normal=r['cases'][0]['marker'];assert normal.startswith(f'PASS096 bytes={total} commands={commands} frames={total*5+16} configs=2 scenario=0 ')
  assert all(c['marker'].startswith('PASS096 ') for c in r['cases'])
  if count==76:
   phases={int(p):int(n) for p,n in re.findall(r'PHASE096 phase=(\d+) commands=(\d+)',(d/'0-1.log').read_text())}
   assert set(phases)==set(range(1,6))
   expected={'0-1'}|{f'{p*100+k}-{i}' for p,n in phases.items() for k in [2,3,6,7] for i in {1,max(1,n//2),n}}|{f'{s}-1' for s in range(1001,1016)}
   assert {c['name'] for c in r['cases']}==expected and len(expected)==76
  ordinary+=count
 assert ordinary==154
 return ordinary

def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--evidence',type=Path);g.add_argument('--runs-root',type=Path)
 a=p.parse_args()
 if a.runs_root:
  verify_runs(a.runs_root.resolve(),'nes-native096-')
 else:
  e=a.evidence.resolve();m=json.loads((ROOT/'analysis/native096-verification.json').read_bytes())
  assert sha(e/'manifest.json')==m['manifest_sha256']
  files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
  for n,h in files.items():
   f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
  for n,h in (m['public_sources']|m['reused_public_sources']).items():assert sha(ROOT/n)==h,n
  verify_runs(e)
  assert (m['host_cases'],m['causal_controls'])==(154,4)
  assert all(not m[n] for n in ['physical','installable','new_arm','new_fit','new_asm','closed_loop_c_rtl_cosimulation','main_menu_reload_verified','actual_configuration_image'])
 print('PASS096:154 native/FatFS/config/READY cases +4 causal controls; source integrity; no hardware approval')
if __name__=='__main__':main()
