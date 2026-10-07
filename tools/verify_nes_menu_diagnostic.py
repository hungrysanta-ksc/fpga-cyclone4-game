# SPDX-License-Identifier: MIT
"""Audit saved062 evidence; this is not a new host/RTL/ARM execution."""
from pathlib import Path
import argparse,hashlib,json,re
from nes_menu_diagnostic import source,host_source,ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence.resolve()
 manifest=read(e/'manifest.json');assert manifest['candidate']=='NES-MENU-DIAGNOSTIC-062'
 for name,h in manifest['files'].items():
  f=(e/name).resolve();assert f.is_relative_to(e) and sha(f)==h,name
 host=read(e/'host-03/result.json');assert host['host_model_pass']
 assert host['marker']=='PASS MENU062 regression=41 input_rejections=18 menu_sessions=16 no_START=1'
 assert host['marker'] in (e/'host-03/host.log').read_text()
 assert (e/'host-03/nes_h1_stm32.c').read_text()==source()
 assert (e/'host-03/sd-platform.c').read_text()==host_source()
 for n,h in host['files'].items():assert sha(e/'host-03'/n)==h,n
 for n in ['nes_h1_stm32.c','nes_menu_diagnostic.c','nes_menu_diagnostic.h','nes_menu_probe.h']:
  assert sha(e/'host-03'/n)==sha(e/'arm-02/src'/n),n
 for n in ['nes_menu_diagnostic.c','nes_menu_diagnostic.h']:
  assert sha(e/'host-03'/n)==sha(ROOT/'src/nes/firmware'/n),n
 for m in ['candidate','menu-release']:
  folder=e/('mutation-'+m+'-02');r=read(folder/'result.json')
  assert r['expected_failure_verified'] and r['exit_code']!=0
  target='candidate.board_seen&&candidate.board_id==0x60&&begin_count==0&&count==0' if m=='candidate' else '!nes_menu_diagnostic_prepared(false)'
  assert 'Assertion failed: '+target in (folder/'host.log').read_text()
 wave=read(e/'wave-01/result.json');fit=read(e/'reused061-fit.json')
 assert wave['candidate']=='NES-MENU-DIAGNOSTIC-062' and not wave['hardware_execution']
 assert wave['host_result_sha256']==sha(e/'host-03/result.json')
 for n,h in fit['sources'].items():
  if n.endswith('.sv'):assert wave['sources'][n]==h,n
 expected={0:(33200,29032,256,0),1:(49472,43288,98304,256)}
 for c in wave['cases']:
  mode=int(c['mode']=='check');log=(e/'wave-01'/c['mode']/'simulation.log').read_text()
  assert c['marker'] in log and not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
  assert tuple(map(int,re.search(r'samples=(\d+) checked=(\d+) pin_bytes=(\d+) verified_bytes=(\d+)',c['marker']).groups()))==expected[mode]
  assert c['waveform_sha256']==sha(e/'wave-01'/c['mode']/'waveform.txt')
 prep=read(e/'arm-02/menu-diagnostic-preparation.json');assert prep['manual_entry_hooks']==3 and not prep['installable']
 for n,h in prep['files'].items():assert sha(e/'arm-02/src'/n)==h,n
 main_dump=(e/'arm-02/main-disassembly.txt').read_text(encoding='utf-8-sig')
 run_dump=(e/'arm-02/menu-run-disassembly.txt').read_text(encoding='utf-8-sig')
 assert len(re.findall(r'\bbl\s+[^\r\n]*<nes_menu_diagnostic_run>',main_dump))==3
 for n in ['nes_menu_diagnostic_prepared','nes_menu_diagnostic_released']:
  assert re.search(r'\bbl\s+[^\r\n]*<'+n+'>',main_dump)
 assert re.search(r'\bbl\s+[^\r\n]*<nes_menu_sd_probe>',run_dump)
 assert 'PASS: compile-only NES062' in (e/'arm-02/build-062.log').read_text()
 print(f'PASS062 frozen evidence files={len(manifest["files"])}; host/menu/causal mutations/GPIO/ARM call sites; no hardware execution')

if __name__=='__main__':main()
