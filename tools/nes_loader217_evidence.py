# SPDX-License-Identifier: MIT
"""217 whole-board gates, actual epoch variants and unchanged216 watchdog proof."""
from pathlib import Path
import argparse,inspect,json
import nes_board207_evidence as prior
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
from check_nes_boundary165 import measurements

s=inspect.getsource(prior.candidate).replace("suffix=f'{index:02d}';", "suffix=f'{index:02d}';index=2;").replace('preparation207.json','preparation217.json')
s=s.replace("test=read(d/('epoch'+suffix)/'result.json')","test=read(BASE/'probes/nes-board207/epoch02/result.json')")
s=s.replace("d/'epoch02/runner.py'","BASE/'probes/nes-board207/epoch02/runner.py'")
ns=dict(prior.__dict__);exec(compile(s,'candidate217','exec'),ns)

def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-loader217'
 boards={}
 for i in [1,2,3,4]:
  io=measurements(d/f'io{i:02d}');(d/f'io{i:02d}/result.json').write_text(json.dumps(io,indent=2)+'\n')
  board,classified=ns['candidate'](d,i);boards[str(i)]=board
  board['inherited207_reference_test']=board.pop('functional')
  board['functional']=read(d/f'epoch{i:02d}/result.json') if i>1 else board['inherited207_reference_test']
  (a.out/f'classified-cdc{i:02d}.json').write_text(json.dumps(classified,indent=2)+'\n')
 test=read(d/'test01/result.json');assert test['passed'] and test['script_sha256']==sha(ROOT/'tools/test_nes_loader217.py')
 for n,h in test['source_pins'].items():assert sha(BASE/n)==h,n
 prep=read(d/'source04/preparation217.json');assert prep['changed']==['nes_rom_loader.sv','nes_source_epoch207.sv']
 assert sha(d/'source01/nes_rom_loader.sv')==sha(d/'source04/nes_rom_loader.sv')
 epochs={}
 for i,tool in [(2,'test_nes_epoch217.py'),(3,'test_nes_epoch217_group.py'),(4,'test_nes_epoch217_publish.py')]:
  epoch=read(d/f'epoch{i:02d}/result.json');epochs[str(i)]=epoch
  assert epoch['passed'] and epoch['script_sha256']==sha(ROOT/'tools'/tool)
  for n,h in epoch['source_pins'].items():assert sha(BASE/n)==h,n
 assert epochs['3']['flag_invariant'] and epochs['3']['declared_extra_registers']==8
 assert epoch['pending_cases']==16 and epoch['wrong_pending_rejected'] and epoch['gray_latency_mem_cycles']==1
 old=BASE/'probes/nes-wait216';p=read(old/'source02/preparation216.json')
 assert prep['baseline']==p['sources']
 for n,h in prep['sources'].items():
  if n not in prep['changed']:assert h==p['sources'][n],n
 reused={}
 for n in ['fixed02','slot-fixed02','guards03']:
  r=read(old/n/'result.json');assert r['passed'];reused[n]=sha(old/n/'result.json')
  assert sha(old/n/'nes_tile205.sv')==sha(d/'source01/nes_tile205.sv')
 assert (d/'paths01/nes_wait216_paths.exitcode').read_text()=='0'
 assert sha(d/'paths01/nes_wait216_paths.tcl')==sha(ROOT/'tools/nes_wait216_paths.tcl')
 arm=read(d/'arm01/preparation-loader217.json')
 for n,h in (arm['copied']|arm['changed']|arm['added']).items():assert sha(d/'arm01'/n)==h,n
 check=read(d/'check01/result.json');assert check['passed'] and check['remaining_margin']==4952
 for f in ['nes_native_runtime165.c','nes_plan_service200.c','nes_planner211.c','nes_resident211.c','nes_native_sink165.c','nes_runtime_board165.inc']:
  assert sha(d/'arm01/src'/f)==sha(BASE/'probes/nes-plan215/arm01/src'/f)
 files=['tools/nes_loader217.py','tools/test_nes_loader217.py','tools/nes_epoch217.py','tools/test_nes_epoch217.py','tools/nes_epoch217_group.py','tools/test_nes_epoch217_group.py','tools/nes_epoch217_publish.py','tools/test_nes_epoch217_publish.py','tools/nes_epoch217_paths.tcl','tools/nes_control217_paths.tcl','tools/nes_loader217_arm.py','tools/check_nes_loader217_arm.py','tools/nes_loader217_evidence.py','docs/nes-loader217-contract.ko.md']
 r=dict(evidence_consistent=True,functional_pass=True,hardware_trial_ready=False,adopted=False,new_package=False,
  selected=['source04','test01','epoch04','mapfit04','timing04','io04','paths04','arm01','check01'],board=board,candidates=boards,loader=test,epochs=epochs,arm=check,
  reused216_watchdog=reused,reused_not_rerun=True,physical=False,fps=None,
  prior_archives=[verify_archive('nes-wait216')],public_sources={n:sha(ROOT/n) for n in files},
  targeted_reports={str(f.relative_to(d)):sha(f) for k in ['paths01','paths02','paths03','paths04'] for f in (d/k).glob('*.rpt')})
 r['targeted_slack_ns']=dict(loader=1.065,serial_to_gray=2.126,control_offset=-.155)
 r['next']='Preserve source04 loader/error and pending-publish epoch; resolve exact SPI bit_count -> byte_count/command CE -> offset predicate/address fanout39, 3LUT/6.006ns/70%routing -.155ns. Preserve byte-boundary/SS-high ID74 queued command, CRC/readback ACK, STOP/overlap/reset. No more epoch formulas/flags or seed-only fits. Whole-board gates then current212 ROM/ASM and217 ARM paired hardware trial; no same215/044.'
 assert not board['related_timing_passed']
 assert (d/'paths04/nes_control217_paths.exitcode').read_text()=='0'
 assert sha(d/'paths04/nes_control217_paths.tcl')==sha(ROOT/'tools/nes_control217_paths.tcl')
 for f,slack in [('wait216-0-loader.rpt','1.065'),('epoch217-0-gray.rpt','2.126'),('control217-0-offset.rpt','-0.155')]:
  assert 'Worst case slack is '+slack in (d/'paths04'/f).read_text(),f
 for k in ['paths02','paths03','paths04']:
  for tool in ['nes_wait216_paths','nes_epoch217_paths']:
   assert (d/k/(tool+'.exitcode')).read_text()=='0'
   assert sha(d/k/(tool+'.tcl'))==sha(ROOT/'tools'/(tool+'.tcl'))
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(ROOT/'analysis/loader217-verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(functional=True,timing=board['related_timing_passed'],le=board['fitted_le'],lab=board['lab'],m9k=board['m9k'],setup=board['timing']['implementation']['setup']['slack'],conditional_io=io['conditional_data_bounds_pass'],new_package=False)))
if __name__=='__main__':main()
