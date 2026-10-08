# SPDX-License-Identifier: MIT
"""Private evidence integrity and conditional normal-session counts, no rerun."""
from pathlib import Path
import argparse,json,re
from nes_spi_boot import ROOT,sha
from nes_session095_replay import preflight

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence.resolve()
 meta=json.loads((ROOT/'analysis/replay095-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 inventory=json.loads((e/'manifest.json').read_bytes())['files'];assert len(inventory)==meta['archived_files']
 for n,h in inventory.items():
  f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 preflight()
 latest=json.loads((ROOT/'analysis/session094-verification.json').read_bytes());capture=json.loads((e/'capture03/result.json').read_bytes())
 assert capture['production_sources']==latest['host_arm_identical'] and capture['guard_ns']==250
 for private,public in [('capture03/executed-capture.py','tools/nes_session095_capture.py'),('capture03/executed-capture.inc','tests/nes-functional/session095_capture.inc'),('faultcapture01/executed-fault-capture.py','tools/nes_session095_fault_capture.py'),('fault02/executed-fault-replay.py','tools/nes_session095_fault_replay.py'),('fault02/session095_fault_tb.sv','tests/nes-functional/session095_fault_tb.sv')]:assert sha(e/private)==meta['public_sources'][public],private
 for n,h in capture['files'].items():assert sha(e/'capture03'/n)==h,n
 fit=json.loads((e/'fit086-result.json').read_bytes());checked=0
 for case,total,key in [('fine_x',81920,'full80-02'),('banks32',98304,'full96-02')]:
  r=json.loads((e/key/'result.json').read_bytes());assert r['full_session'] and r['guard_abstraction']
  assert r['guard_full_state_bits']==34 and r['guard_cycle_period_ns']==4000 and r['synthetic_guard_ns']==250
  assert r['driver_sha256']==sha(e/key/'executed-driver.py')==meta['public_sources']['tools/nes_session095_replay.py']
  assert r['sources']['session095_tb.sv']==sha(e/key/'executed-testbench.sv')==meta['public_sources']['tests/nes-functional/session095_tb.sv']
  assert r['host_result_sha256']==sha(e/'capture03/result.json')
  assert r['mcu_production_sources']==latest['host_arm_identical']
  for n,h in r['production_sources'].items():assert fit['sources'][n]==h,n
  m=re.search(r'bytes=(\d+) frames=(\d+) writes=(\d+) reads=(\d+) ACK=(\d+) checked=(\d+) FINISH=(\d+) STOP=(\d+)',r['marker']);assert m
  assert tuple(map(int,m.groups()))==(total,total*5+16,total,total,total,total*280+752,1,1)
  checked+=int(m[6]);assert 'no_RUN=1' in r['marker']
  for folder in ['capture02','capture03']:assert sha(e/folder/(case+'.trace'))==r['trace_sha256']
  assert r['trace_sha256']==capture['cases'][case]['trace_sha256']
 assert checked==50464224
 for key in ['response01','proofnegative01']:
  r=json.loads((e/key/'result.json').read_bytes());assert r['expected_failure']
 faults=json.loads((e/'fault02/result.json').read_bytes());assert len(faults['cases'])==3
 assert [r['negative'] for r in faults['cases']]==[False,False,True]
 assert faults['host_result_sha256']==sha(e/'faultcapture01/result.json')
 fault_capture=json.loads((e/'faultcapture01/result.json').read_bytes());assert fault_capture['production_sources']==latest['host_arm_identical']
 for r in faults['cases']:
  log=e/'fault02'/(r['case']+('-negative' if r['negative'] else '')+'.log');assert sha(log)==r['log_sha256'] and r['marker'] in log.read_text()
 for n,h in faults['production_sources'].items():assert fit['sources'][n]==h,n
 assert not meta['physical'] and not meta['installable'] and not meta['continuous_full_guard_simulation']
 assert not meta['closed_loop_c_rtl_cosimulation'] and meta['synthetic_guard_ns']==250
 print('PASS095: conditional full80/96KiB,901152frames/50464224bits,34-bit guard cycle,2 raw-lock cases/3 controls; no hardware approval')
if __name__=='__main__':main()
