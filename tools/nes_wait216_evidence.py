# SPDX-License-Identifier: MIT
"""216 consistency checks; functional PASS does not override failed timing."""
from pathlib import Path
import argparse,inspect,json
import nes_board207_evidence as prior
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
from check_nes_boundary165 import measurements

# Reuse the existing all-corner/CDC/reset/I/O rules, not looser216 thresholds.
# Epoch207 logic is byte-identical; reuse its functional proof explicitly.
s=inspect.getsource(prior.candidate).replace('preparation207.json','preparation216.json')
s=s.replace("test=read(d/('epoch'+suffix)/'result.json')","test=read(BASE/'probes/nes-board207/epoch02/result.json')")
s=s.replace("d/'epoch02/runner.py'","BASE/'probes/nes-board207/epoch02/runner.py'")
ns=dict(prior.__dict__);exec(compile(s,'candidate216','exec'),ns)

def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-wait216'
 io=measurements(d/'io02');(d/'io02/result.json').write_text(json.dumps(io,indent=2)+'\n')
 board,classified=ns['candidate'](d,2)
 (a.out/'classified-cdc.json').write_text(json.dumps(classified,indent=2)+'\n')
 tests={}
 for n in ['long01','short01','fixed01','slot-old01','slot-fixed01','fixed02','slot-fixed02','guards02','guards03']:
  r=read(d/n/'result.json');assert r['passed'],n;tests[n]=dict(result_sha256=sha(d/n/'result.json'),codes=r.get('codes'),cycles=r.get('cycles'),candidate=r.get('candidate'),expect_fault=r.get('expect_fault'))
  if n in ['fixed02','slot-fixed02','guards03']:
   assert sha(d/n/'nes_tile205.sv')==sha(d/'source02/nes_tile205.sv')
   for f,h in r['source_pins'].items():
    q=Path(f);assert sha(q if q.is_absolute() else BASE/q)==h,f
  if n in ['long01','slot-old01']:
   assert '00d704800001000000000000000000000000007f' in (d/n/'host.log').read_text()
   assert 'tile=1 arbiter=0 denied=0 lease=0 spi=0 batch=0 bulk=0 consume=0 command=0' in (d/n/'rtl.log').read_text()
  if n in ['short01','fixed01','slot-fixed01','fixed02','slot-fixed02']:
   assert 'PASS WAIT216 frames=3 plans=57 chunks=55 bytes=1072' in (d/n/'host.log').read_text()
 prep=read(d/'arm01/preparation-wait216.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(d/'arm01'/n)==h,n
 check=read(d/'check02/result.json');assert check['passed'] and check['remaining_margin']==4952
 assert (d/'paths01/nes_wait216_paths.exitcode').read_text()=='0'
 assert sha(d/'paths01/nes_wait216_paths.tcl')==sha(ROOT/'tools/nes_wait216_paths.tcl')
 assert 'Worst case slack is -0.320' in (d/'paths01/wait216-0-loader.rpt').read_text()
 assert 'Worst case slack is 36.322' in (d/'paths01/wait216-0-counter.rpt').read_text()
 for f in ['nes_native_runtime165.c','nes_plan_service200.c','nes_planner211.c','nes_resident211.c','nes_native_sink165.c','nes_runtime_board165.inc']:
  assert sha(d/'arm01/src'/f)==sha(BASE/'probes/nes-plan215/arm01/src'/f)
 first={}
 for view in ['nominal','implementation']:
  rows=prior.rows(d/'timing01'/(view+'-paths204.tsv'))
  first[view]={kind:min((r for r in rows if r['kind']==kind and ((r['from_clock']=='nes')==(r['to_clock']=='nes'))),key=lambda r:float(r['slack'])) for kind in ['setup','hold']}
 files=['tools/nes_wait216.py','tools/test_nes_wait216.py','tools/test_nes_wait216_guards.py','tools/nes_wait216_arm.py','tools/check_nes_wait216_arm.py','tools/nes_wait216_evidence.py','tools/nes_wait216_paths.tcl','tools/nes_board207_evidence.py','src/nes/rtl/nes_tile205.sv','tests/nes-functional/wait216_guards_tb.sv','docs/nes-wait216-contract.ko.md']
 r=dict(evidence_consistent=True,functional_pass=True,hardware_trial_ready=False,adopted=False,
  selected=['source02','fixed02','slot-fixed02','guards03','mapfit02','timing02','io02','paths01','arm01','check02'],
  source01_timing=first,board=board,tests=tests,arm=check,
  physical_root_cause_confirmed=False,reproduced_identical_hardware_response=True,physical=False,fps=None,new_package=False,
  targeted_paths=dict(loader_slack_ns=-.320,loader_data_ns=6.179,loader_logic_levels=5,loader_interconnect_percent=64,tile_counter_slack_ns=36.322,
   reports={str(f.relative_to(d)):sha(f) for f in (d/'paths01').glob('wait216-*.rpt')}),
  prior_archives=[verify_archive('nes-plan215'),verify_archive('nes-game215-hardware01')],
  public_sources={n:sha(ROOT/n) for n in files},next='Resolve exact loader load_valid -> error_code[1] related-clock -0.320ns path without timeout/clock/SDC waiver; preserve216 waiting semantics and21-bit counter, then full timing/paired212ROM/ASM before216 hardware FIRSTLEVELSCROLL. No same215 test or seed-only FIT loop.')
 assert not board['related_timing_passed']
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(ROOT/'analysis/wait216-verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(functional=True,timing=board['related_timing_passed'],le=board['fitted_le'],lab=board['lab'],m9k=board['m9k'],setup=board['timing']['implementation']['setup']['slack'],conditional_io=io['conditional_data_bounds_pass'],new_package=False)))
if __name__=='__main__':main()
