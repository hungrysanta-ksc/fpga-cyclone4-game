# SPDX-License-Identifier: MIT
"""Audit the physical candidate; passing this verifier does NOT approve timing."""
from pathlib import Path
import argparse,csv,json,re
from nes_cdc125_sta import ROOT,sha

def review(e):
 t=e/'test02';f=e/'fit02'
 m=json.loads((t/'board134.json').read_bytes());assert m['passed'] and not m['physical_trial']
 assert set(m['results'])=={'normal-0','normal-3500','torn-negative'}
 for phase in [0,3500]:
  s=(t/f'normal-{phase}.log').read_text(errors='replace')
  assert f'PASS134 status=7 actual_sample_events=3356 injected_events=4 checks=237885 phase_ps={phase}' in s
  assert '** Fatal:' not in s
 assert '** Fatal: BOARD134 coherent snapshot' in (t/'torn-negative.log').read_text(errors='replace')
 for n in ['nes_live_joint.sv','nes_run_observer134.sv','fxpak_nes_run134_top.sv']:
  assert sha(t/n)==sha(f/n),n
 for n in ['nes_run_observer134.sv','fxpak_nes_run134_top.sv']:
  assert sha(f/n)==sha(ROOT/'src/nes/diagnostic'/n),n
 assert sha(t/'board134_tb.sv')==sha(ROOT/'tests/nes-functional/board134_tb.sv')
 assert sha(f/'executed-board134.py')==sha(ROOT/'tools/nes_board134.py')
 assert sha(f/'executed-fit134.py')==sha(ROOT/'tools/nes_board134_fit.py')
 assert sha(f/'timing134.tcl')==sha(ROOT/'tools/nes_board134_timing.tcl')
 # test02 preceded only the unused-pin QSF assignment; simulation logic identical.
 delta=' qsf.append(\'set_global_assignment -name RESERVE_ALL_UNUSED_PINS "AS INPUT TRI-STATED"\')\n'
 assert (f/'executed-board134.py').read_text().replace(delta,'')==(t/'executed-board134.py').read_text()
 base=e.parents[1]/'nes-counter131/evidence'
 bm=json.loads((ROOT/'analysis/counter131-verification.json').read_bytes())
 assert sha(base/'manifest.json')==bm['manifest_sha256']
 inputs=json.loads((f/'materialization.json').read_bytes())['inputs']
 for n,h in inputs.items():assert sha(base/n)==h,n
 assert json.loads((t/'materialization.json').read_bytes())['inputs']==inputs
 pins=json.loads((f/'pin-map.json').read_bytes());assert pins['physical_bits']==95 and pins['virtual_bits']==0
 assert pins['source_sha256']==sha(ROOT/'src/fpga/pin.qsf')
 report=(f/'output_files/board.pin').read_text(errors='replace');actual={}
 for line in report.splitlines():
  cells=[x.strip() for x in line.split(':')]
  if len(cells)>=3 and cells[0] in pins['ports']:actual[cells[0]]=cells[1]
 for n,d in pins['ports'].items():assert actual[n]=='{}'.format(d['pin'].removeprefix('PIN_')),(n,d)
 assert len(actual)==95 and not re.search(r'^RESERVED_OUTPUT',report,re.M)
 assert json.loads((f/'fit134.json').read_bytes())['phases']=={'map':0,'fit':0,'sta':0}
 summary=(f/'output_files/board.fit.summary').read_text(errors='replace')
 assert '12,001 / 15,408' in summary and 'Total virtual pins : 0' in summary and '95 / 166' in summary
 rows=list(csv.DictReader((f/'timing134.tsv').open(),delimiter='\t'));assert len(rows)==24
 same=[r for r in rows if r['group']=='same_clock'];assert len(same)==18
 setup=min(float(r['slack']) for r in same if r['type']=='setup')
 hold=min(float(r['slack']) for r in same if r['type']=='hold')
 assert setup==-0.330 and hold==0.179 # Failed timing is retained, not waived.
 return dict(status_reads=14,actual_cpu_sample_events=6712,injected_saturation_events=8,
             pin_assignments_checked=95,virtual_pins=0,logic_elements=12001,LAB=893,M9K=12,
             same_clock_setup_min_ns=setup,same_clock_hold_min_ns=hold,
             raw_setup_min_ns=min(float(r['slack']) for r in rows if r['type']=='setup'),
             same_clock_timing_pass=False,full_timing_pass=False,installable=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
 meta=json.loads((ROOT/'analysis/board134-verification.json').read_bytes())
 assert sha(a.evidence/'manifest.json')==meta['manifest_sha256']
 for n,h in json.loads((a.evidence/'manifest.json').read_bytes())['files'].items():assert sha(a.evidence/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(a.evidence)==meta['checks']
 print('PASS134 integrity/function/pins; timing FAIL retained; NOT INSTALLABLE')
if __name__=='__main__':main()
