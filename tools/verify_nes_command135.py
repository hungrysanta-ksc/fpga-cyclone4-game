# SPDX-License-Identifier: MIT
"""Verify135 evidence; same-clock pass does not waive CDC, reset or external IO."""
from pathlib import Path
import argparse,csv,json,re
from nes_cdc125_sta import ROOT,sha

ATTR='(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) '
OLD_DOC='Reuse134 physical shell; change only the SPI validation register boundary.'
NEW_DOC='Reuse134 shell with factored SPI/boot checks and targeted loader mapping.'

def text(p):return p.read_text(encoding='utf8')
def rows(p):
 with p.open() as f:return list(csv.DictReader(f,delimiter='\t'))

def review(e):
 t=e/'test02';f=e/'fit03';baseline=e.parents[1]
 m=json.loads((t/'test135.json').read_bytes())
 assert m['passed'] and not m['full_load_check'] and not m['physical_trial']
 expected={'equivalence':'PASS135 cause equivalence cases=4194304',
 'boot-equivalence':'PASS135 boot sticky equivalence cases=4096',
 'decoder-60':'PASS SPI CHECK CONTROL checks=166 negative_cases=18',
 'decoder-18':'PASS SPI CHECK CONTROL checks=166 negative_cases=18',
 'board-0':'PASS134 status=7 actual_sample_events=3356 injected_events=4 checks=237885 phase_ps=0',
 'board-3500':'PASS134 status=7 actual_sample_events=3356 injected_events=4 checks=237885 phase_ps=3500',
 'negative-cause':'** Fatal: CAUSE135 mismatch',
 'negative-fault':'** Fatal: CHECK CONTROL 160 RETIRE128 hard fault wins START',
 'negative-owner':'** Fatal: BOOT135 mismatch'}
 assert set(m['runs'])==set(expected)
 for n,token in expected.items():
  log=text(t/(n+'.log'));assert token in log,n
  if not n.startswith('negative'):assert '** Fatal:' not in log,n
 for n in ['decoder-60','decoder-18']:
  assert 'PASS128 boundary hard_fault_start=1 raw_reset_pending=1 clock_stop=1 overlapping_frame=1' in text(t/(n+'.log'))
 base=baseline/'nes-board134/evidence';bm=json.loads((ROOT/'analysis/board134-verification.json').read_bytes())
 assert sha(base/'manifest.json')==bm['manifest_sha256']
 basepins=json.loads((base/'manifest.json').read_bytes())['files']
 fm=json.loads((f/'materialization135.json').read_bytes());tm=json.loads((t/'materialization135.json').read_bytes())
 assert fm['base_manifest']==tm['base_manifest']==bm['manifest_sha256']
 assert set(fm['changed'])=={'nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv'}
 assert set(tm['changed'])=={'nes_rom_spi.sv','nes_rom_boot.sv'}
 assert set(fm['inputs'])==set(tm['inputs'])
 for n,h in fm['inputs'].items():
  assert sha(f/n)==h and sha(t/n)==tm['inputs'][n],n
  assert sha(base/'fit02'/n)==basepins['fit02/'+n],n
  if n in fm['changed']:
   d=fm['changed'][n];assert d['before']==basepins['fit02/'+n] and d['after']==h
   assert h==sha(ROOT/'src/nes/diagnostic'/(Path(n).stem+'135.sv'))
   if n=='nes_rom_loader.sv':
    s=text(f/n);decl='output reg [16:0] loaded_bytes,';assert s.count(ATTR+decl)==1
    assert s.replace(ATTR+decl,decl)==text(t/n)==text(base/'fit02'/n)
   else:assert h==tm['inputs'][n]
  else:assert h==tm['inputs'][n]==basepins['fit02/'+n],n
 for n in ['nes_clock_pll123.v','nes_run_observer134.sv','fxpak_nes_run134_top.sv','board.qsf','board.sdc']:
  assert sha(f/n)==sha(base/'fit02'/n),n
 for n in ['nes_run_observer134.sv','fxpak_nes_run134_top.sv']:
  assert sha(f/n)==sha(t/n)==sha(ROOT/'src/nes/diagnostic'/n)
 for n in ['command135_diff_tb.sv','boot135_diff_tb.sv','board134_tb.sv','run133_pll_model.sv']:
  assert sha(t/n)==sha(ROOT/'tests/nes-functional'/n),n
 for n,mod in [('nes_rom_spi.sv','nes_rom_spi_check'),('nes_rom_boot.sv','nes_rom_boot')]:
  target='baseline135' if 'spi' in n else 'baseline_boot135'
  assert text(t/(target+'.sv'))==text(base/'fit02'/n).replace('module '+mod+'(','module '+target+'(')
 old=baseline/'nes-command128/evidence';meta=json.loads((ROOT/'analysis/command128-verification.json').read_bytes())
 assert sha(old/'manifest.json')==meta['manifest_sha256']
 oldpins=json.loads((old/'manifest.json').read_bytes())['files'];n='test06/spi_readback_control_tb.sv'
 assert sha(old/n)==oldpins[n]==sha(t/Path(n).name)
 # Publication changes only clarify a docstring and correct the printed negative count.
 materializer=text(ROOT/'tools/nes_command135.py').replace(NEW_DOC,OLD_DOC)
 assert materializer==text(f/'executed-command135.py')
 assert materializer.replace(",'nes_rom_loader'",'')==text(t/'executed-nes_command135.py')
 assert text(ROOT/'tools/nes_command135_test.py').replace('three negatives rejected','two negatives rejected')==text(t/'executed-nes_command135_test.py')
 assert sha(f/'executed-fit135.py')==sha(ROOT/'tools/nes_command135_fit.py')
 assert sha(f/'timing135.tcl')==sha(ROOT/'tools/nes_command135_timing.tcl')
 pins=json.loads((f/'pin-map.json').read_bytes());assert pins['physical_bits']==95 and pins['virtual_bits']==0
 assert pins['source_sha256']==sha(ROOT/'src/fpga/pin.qsf')
 report=text(f/'output_files/board.pin');actual={}
 for line in report.splitlines():
  cells=[x.strip() for x in line.split(':')]
  if len(cells)>=3 and cells[0] in pins['ports']:actual[cells[0]]=cells[1]
 for n,d in pins['ports'].items():assert actual[n]==d['pin'].removeprefix('PIN_'),n
 assert len(actual)==95 and not re.search(r'^RESERVED_OUTPUT',report,re.M)
 assert json.loads((f/'fit135.json').read_bytes())['phases']=={'map':0,'fit':0,'sta':0}
 summary=text(f/'output_files/board.fit.summary')
 for token in ['12,026 / 15,408','Total registers : 4088','Total virtual pins : 0','95 / 166','Total PLLs : 1 / 4']:assert token in summary
 fit=(f/'output_files/board.fit.rpt').read_text(encoding='latin1');assert re.search(r'Total LABs:.*?; 885 / 963',fit) and re.search(r'; M9Ks\s+; 12 / 56',fit)
 r=rows(f/'timing134.tsv');assert len(r)==24
 same=[x for x in r if x['group']=='same_clock'];assert len(same)==18
 setup=min(float(x['slack']) for x in same if x['type']=='setup');hold=min(float(x['slack']) for x in same if x['type']=='hold')
 assert setup==.152 and hold==.180
 assert min(float(x['slack']) for x in r if x['type']=='setup')==-6.767
 ucp=text(f/'unconstrained134.rpt')
 assert re.search(r'Unconstrained Input Ports\s+; 19\s+;',ucp)
 assert re.search(r'Unconstrained Output Ports\s+; 44\s+;',ucp)
 targets=rows(f/'targeted135.tsv');assert len(targets)==9
 targetmins={n:min(float(x['slack']) for x in targets if x['group']==n) for n in ['pending_causes','check_failed','loaded_bytes']}
 assert targetmins==dict(pending_causes=.355,check_failed=1.201,loaded_bytes=.190)
 regs=rows(f/'registers135.tsv');assert len(regs)==17 and len({x['register'] for x in regs})==17
 assert all(x['source'].endswith('|d') and x['register']==x['destination'] for x in regs)
 for n,expected_min in [('fit01',-.183),('fit02',-.318)]:
  failed=rows(e/n/'timing134.tsv')
  assert min(float(x['slack']) for x in failed if x['group']=='same_clock' and x['type']=='setup')==expected_min
 return dict(cause_combinations=4194304,boot_clocked_combinations=4096,decoder_checks_per_phase=166,
 negative_controls=3,actual_cpu_samples=6712,injected_saturation_events=8,status_reads=14,
 pin_assignments_checked=95,virtual_pins=0,logic_elements=12026,LAB=885,registers=4088,M9K=12,PLL=1,
 same_clock_setup_min_ns=setup,same_clock_hold_min_ns=hold,target_setup_min_ns=targetmins,
 loaded_bytes_registers_without_enable=17,raw_setup_min_ns=-6.767,
 same_clock_timing_pass=True,full_timing_pass=False,installable=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
 meta=json.loads((ROOT/'analysis/command135-verification.json').read_bytes())
 assert sha(a.evidence/'manifest.json')==meta['manifest_sha256']
 for n,h in json.loads((a.evidence/'manifest.json').read_bytes())['files'].items():assert sha(a.evidence/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(a.evidence)==meta['checks']
 print('PASS135 integrity/function/physical pins/same-clock timing; CDC/reset/IO open; NOT INSTALLABLE')
if __name__=='__main__':main()
