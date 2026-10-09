# SPDX-License-Identifier: MIT
"""Recheck frozen full-frame evidence, not a new simulator/board execution."""
from pathlib import Path
import argparse,json,hashlib,shutil,tempfile
from nes_core_frames121 import compare

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 root=Path(__file__).resolve().parents[1];meta=json.loads((root/'analysis/frames121-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 manifest=json.loads((e/'manifest.json').read_bytes())
 assert len(manifest['files'])==meta['archived_files']
 for n,h in manifest['files'].items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(root/n)==h,n
 result=json.loads((e/'full01/result.json').read_bytes())
 assert result['passed'] and result['read_cycles']==8 and result['access_ns']==70
 expected={(p,c) for p in (3.5,0.0,11.25) for c in ('fine_x','banks32')}
 assert len(result['cases'])==6 and {(r['phase_ns'],r['case']) for r in result['cases']}==expected
 historical=json.loads((root/'analysis/rom-physical-artifacts.json').read_bytes())
 prefix='analysis/local-rom-physical-052/live/'
 pins={v['path'][len(prefix):]:v['sha256'] for rows in historical.values() if isinstance(rows,list) for v in rows if isinstance(v,dict) and v.get('path','').startswith(prefix)}
 assert meta['cases']==result['cases']
 for n,h in result['inputs'].items():assert pins[n]==h,n
 for n,h in result['sources'].items():
  assert sha(e/'full01'/n)==h,n
  if n not in ('nes_rom_physical.sv','ncr1_live_tb.sv'):assert h==result['inputs'][n],n
 original=e/'oracle052/ncr1_live_tb.sv'
 assert sha(original)==pins['ncr1_live_tb.sv']
 expected_tb=original.read_text().replace('module ncr1_live_tb;','module ncr1_live_tb #(parameter realtime PHASE121=3.5);').replace('.READ_CYCLES(3)','.READ_CYCLES(8)').replace('initial begin #3.5;forever #5.952381 mem_clk','initial begin #(PHASE121);forever #5.952381 mem_clk').replace('rom_physical_model #(.FIXTURE(1))','rom_physical_model #(.FIXTURE(1),.ACCESS_NS(70.0))')
 assert (e/'full01/ncr1_live_tb.sv').read_text()==expected_tb
 with tempfile.TemporaryDirectory(prefix='nes-verify121-') as scratch:
  for r in result['cases']:
   group=e/'full01'/f"phase{int(r['phase_ns']*1000):05d}"
   assert sha(group/r['case']/'simulation.log')==r['log_sha256']
   log=(group/r['case']/'simulation.log').read_text()
   assert f"-gPHASE121={r['phase_ns']} " in log
   # Existing decoder emits packet files: use a scratch copy, never rewrite evidence.
   work=Path(scratch)/group.name
   shutil.copytree(group/r['case'],work/r['case'])
   check=compare(work,e/'oracle052',r['case'],pins)
   for n,v in check.items():assert r[n]==v,(r['case'],n)
 assert meta['frames']==24 and meta['pixels']==1474560
 print('PASS121 six full actual-core cases /24 frames /1474560 pixels / baseline byte+event equivalence / source and archive hashes')
if __name__=='__main__':main()
