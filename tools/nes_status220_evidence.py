# SPDX-License-Identifier: MIT
"""Pin220 functional evidence and full-board timing without changing gates."""
from pathlib import Path
import argparse,inspect,json
import nes_board207_evidence as prior
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
from check_nes_boundary165 import measurements
from nes_status220 import transform
from nes_response220 import transform as response
s=inspect.getsource(prior.candidate).replace("suffix=f'{index:02d}';", "suffix=f'{index:02d}';index=2;").replace('preparation207.json','preparation220.json')
s=s.replace("test=read(d/('epoch'+suffix)/'result.json')","test=read(BASE/'probes/nes-board207/epoch02/result.json')")
s=s.replace("d/'epoch02/runner.py'","BASE/'probes/nes-board207/epoch02/runner.py'")
ns=dict(prior.__dict__);exec(compile(s,'candidate220','exec'),ns)
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-status220';old=BASE/'probes/nes-retire219'
 boards={}
 for i in [1,2]:
  io=measurements(d/f'io0{i}');(d/f'io0{i}/result.json').write_text(json.dumps(io,indent=2)+'\n')
  board,classified=ns['candidate'](d,i)
  (a.out/f'classified-cdc0{i}.json').write_text(json.dumps(classified,indent=2)+'\n')
  board['inherited207_reference_test']=board.pop('functional');boards[str(i)]=board
 prep=read(d/'source01/preparation220.json');base=read(old/'source02/preparation219.json')
 assert prep['baseline']==base['sources'] and prep['changed']==['nes_rom_loader.sv']
 for n,h in prep['sources'].items():
  if n!='nes_rom_loader.sv':assert h==base['sources'][n],n
 assert (d/'source01/nes_rom_loader.sv').read_text()==transform((old/'source02/nes_rom_loader.sv').read_text())
 prep2=read(d/'source02/preparation220.json');assert prep2['baseline']==base['sources']
 for n,h in prep2['sources'].items():
  if n!='nes_rom_spi.sv':assert h==prep['sources'][n],n
 assert (d/'source02/nes_rom_spi.sv').read_text()==response((d/'source01/nes_rom_spi.sv').read_text())
 spi=read(d/'spi02/result.json');assert spi['passed'] and spi['retire_checks']==327680
 assert spi['source_sha256']==sha(d/'source02/nes_rom_spi.sv') and spi['reference_sha256']==sha(d/'source01/nes_rom_spi.sv')
 for n,h in spi['sources'].items():assert sha(d/'spi02'/n)==h,n
 for n,h in spi['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:assert sha(d/'spi02'/n)==sha(d/'source02'/n),n
 test=read(d/'test03/result.json');assert test['passed'] and test['reset_checks']==18432
 for n,h in test['source_pins'].items():assert sha(BASE/n)==h,n
 for n,h in test['sources'].items():assert sha(d/'test03'/n)==h,n
 for n,h in test['positive_logs_reused_not_rerun'].items():
  assert sha(Path(n))==h and sha(d/'test03'/Path(n).name)==h,n
 assert test['script_sha256']==sha(ROOT/'tools/test_nes_status220.py')
 assert (d/'test03/candidate.sv').read_text()==(d/'source01/nes_rom_loader.sv').read_text()
 for n in ['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_physical.sv']:assert sha(d/'test03'/n)==sha(d/'source01'/n),n
 for folder in ['paths01','paths02']:
  for tool in ['nes_wait216_paths','nes_epoch217_paths','nes_control218_paths','nes_payload218_paths','nes_finish218_paths','nes_fault219_paths','nes_snapshot219_paths']:
   assert (d/folder/(tool+'.exitcode')).read_text()=='0'
   assert sha(d/folder/(tool+'.tcl'))==sha(ROOT/'tools'/(tool+'.tcl'))
 inherited=read(old/'evidence03/result.json')
 r=dict(evidence_consistent=True,functional_pass=True,hardware_trial_ready=False,adopted=False,new_package=False,
  scope='Board qualification only; paired ARM/ASM/ROM and final installation readiness are recorded in release220-verification.json.',
  selected=['source02','test03','spi02','mapfit02','timing02','io02','paths02'],board=board,candidates=boards,test=test,spi=spi,
  reused_not_rerun=inherited['reused_not_rerun'],spi219_reused_not_rerun=dict(result_sha256=sha(old/'spi01/result.json')),
  physical=False,fps=None,prior_archives=[verify_archive('nes-retire219')],
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_status220.py','tools/test_nes_status220.py','tools/nes_response220.py','tools/test_nes_response220.py','tools/nes_status220_evidence.py','docs/nes-status220-contract.ko.md']},
  targeted_reports={str(f.relative_to(d)):sha(f) for p in ['paths01','paths02'] for f in (d/p).glob('*.rpt')},
  next='Whole-board related timing must pass before new ARM/current212 ROM paired ASM/ZIP. Preserve reset-to-IDLE invariant, original status snapshot edge and command/STOP/error/WRITE-drain semantics. No clock/SDC relaxation or seed-only fits.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(ROOT/'analysis/status220-verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(functional=True,timing=board['related_timing_passed'],le=board['fitted_le'],ff=board['registers'],lab=board['lab'],m9k=board['m9k'],setup=board['timing']['implementation']['setup']['slack'],conditional_io=io['conditional_data_bounds_pass'],new_package=False)))
if __name__=='__main__':main()
