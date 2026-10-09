# SPDX-License-Identifier: MIT
"""Recheck frozen safe-reader evidence; no new simulation or board claim."""
from pathlib import Path
import argparse,json,hashlib,shutil,tempfile,re
from nes_safe_reader122 import compare

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 root=Path(__file__).resolve().parents[1];meta=json.loads((root/'analysis/safe122-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==meta['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(root/n)==h,n
 for n,h in meta['review_inputs'].items():assert sha(root/n)==h,n
 for label in ('failed01','unit01','full02','unit02'):
  r=json.loads((e/label/'result.json').read_bytes())
  for n,h in r['sources'].items():assert sha(e/label/n)==h,(label,n)
  assert sha(e/label/'nes_rom_physical.sv')==sha(root/'src/nes/diagnostic/nes_diag_safe_rom_physical.sv')
 failed=json.loads((e/'failed01/result.json').read_bytes());assert not failed['passed'] and failed['read_cycles']==8 and failed['cases']==[]
 log=(e/'failed01/phase03500/fine_x/simulation.log').read_text()
 assert 'ROM DEADLINE/PROTOCOL error=1 tick=852209 cpu=000e184 ppu=201ffa' in log and 'PASS LIVE NES' not in log
 raw=re.findall(r'ROM HISTORY ([0-9a-f]+)',log);assert len(raw)==16
 widths=[('respaddr',22),('addr',22),('error',1),('response',1),('ready',1),('request',1),('ppuvalid',1),('cpuvalid',1),('ppusample',1),('cpusample',1),('ppuread',1),('cpuread',1),('ppu',22),('cpu',25),('tick',32)]
 history=[]
 for line in raw:
  v=int(line,16);row={}
  for n,w in widths:row[n]=v&((1<<w)-1);v>>=w
  assert v==0;history.append(row)
 assert history==json.loads((e/'failure01.json').read_bytes())['history']
 old=json.loads((e/'unit01/result.json').read_bytes());unit=json.loads((e/'unit02/result.json').read_bytes())
 for label,r,cycles,step in [('unit01',old,8,750),('unit02',unit,16,375)]:
  assert r['passed'] and r['negative110_rejected'] and r['read_cycles']==cycles
  assert [x['phase_ps'] for x in r['cases']]==list(range(0,step*16,step))
  assert sum(x['completed'] for x in r['cases'])==8400 and sum(x['canceled'] for x in r['cases'])==208
  for x in r['cases']:
   log=(e/label/f"phase-{x['phase_ps']}.log").read_text()
   assert 'PASS PHYSICAL' in log and '** Fatal:' not in log
   assert x['accepted']==x['completed']+x['canceled']
  assert '** Fatal: PHYSICAL check' in (e/label/'late110.log').read_text()
 assert unit['negative_hold_rejected'] and '** Fatal: SAFE122 hold interval' in (e/'unit02/negative-no-hold.log').read_text()
 assert sha(e/'unit02/negative-no-hold.sv')==unit['negative_source_sha256']
 for r in unit['cases']:assert r['setup_checks']>=525 and r['hold_checks']>=525
 result=json.loads((e/'full02/result.json').read_bytes())
 assert result['passed'] and result['read_cycles']==16 and result['access_ns']==70
 expected={(p,c) for p in (3.5,0.0,5.625) for c in ('fine_x','banks32')}
 assert len(result['cases'])==6 and {(r['phase_ns'],r['case']) for r in result['cases']}==expected
 assert meta['cases']==result['cases'] and meta['unit_cases']==unit['cases']
 historical=json.loads((root/'analysis/rom-physical-artifacts.json').read_bytes());prefix='analysis/local-rom-physical-052/live/'
 pins={v['path'][len(prefix):]:v['sha256'] for rows in historical.values() if isinstance(rows,list) for v in rows if isinstance(v,dict) and v.get('path','').startswith(prefix)}
 for n,h in result['inputs'].items():assert pins[n]==h,n
 for n,h in result['sources'].items():
  if n not in ('nes_rom_physical.sv','ncr1_live_tb.sv'):assert h==result['inputs'][n],n
 original=e/'oracle052/ncr1_live_tb.sv';assert sha(original)==pins['ncr1_live_tb.sv']
 expected_tb=original.read_text().replace('module ncr1_live_tb;','module ncr1_live_tb #(parameter realtime PHASE122=3.5);').replace('.READ_CYCLES(3)','.READ_CYCLES(16)').replace('initial begin #3.5;forever #5.952381 mem_clk','initial begin #(PHASE122);forever #2.9761905 mem_clk').replace('rom_physical_model #(.FIXTURE(1))','rom_physical_model #(.FIXTURE(1),.ACCESS_NS(70.0))').replace('physical(.clk(clk),',"physical(.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),.clk(clk),")
 assert (e/'full02/ncr1_live_tb.sv').read_text()==expected_tb
 assert sha(e/'full02/executed-driver.py')==sha(root/'tools/nes_safe_reader122.py')
 assert sha(e/'unit02/executed-driver.py')==sha(root/'tools/nes_safe122_unit.py')
 with tempfile.TemporaryDirectory(prefix='nes-verify122-') as scratch:
  for r in result['cases']:
   group=e/'full02'/f"phase{int(r['phase_ns']*1000):05d}"
   assert sha(group/r['case']/'simulation.log')==r['log_sha256']
   assert f"-gPHASE122={r['phase_ns']} " in (group/r['case']/'simulation.log').read_text()
   work=Path(scratch)/group.name;shutil.copytree(group/r['case'],work/r['case'])
   for n,v in compare(work,e/'oracle052',r['case'],pins).items():assert r[n]==v,(r['case'],n)
 assert meta['frames']==24 and meta['pixels']==1474560 and not meta['new_hardware_package']
 print('PASS122 baseline deadline reproduced / 24 frames pixel+event equivalence / 16-phase pins /110ns and no-HOLD rejection / immutable hashes')
if __name__=='__main__':main()
