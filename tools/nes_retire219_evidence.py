# SPDX-License-Identifier: MIT
"""Pin219 same-edge control proof and unchanged whole-board acceptance gates."""
from pathlib import Path
import argparse,inspect,json
import nes_board207_evidence as prior
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
from check_nes_boundary165 import measurements
s=inspect.getsource(prior.candidate).replace("suffix=f'{index:02d}';", "suffix=f'{index:02d}';index=2;").replace('preparation207.json','preparation219.json')
s=s.replace("test=read(d/('epoch'+suffix)/'result.json')","test=read(BASE/'probes/nes-board207/epoch02/result.json')")
s=s.replace("d/'epoch02/runner.py'","BASE/'probes/nes-board207/epoch02/runner.py'")
ns=dict(prior.__dict__);exec(compile(s,'candidate219','exec'),ns)
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-retire219';old=BASE/'probes/nes-boundary218'
 boards={}
 for i in [1,2]:
  io=measurements(d/f'io0{i}');(d/f'io0{i}/result.json').write_text(json.dumps(io,indent=2)+'\n')
  board,classified=ns['candidate'](d,i)
  (a.out/f'classified-cdc0{i}.json').write_text(json.dumps(classified,indent=2)+'\n')
  board['inherited207_reference_test']=board.pop('functional');boards[str(i)]=board
 prep=read(d/'source01/preparation219.json');base=read(old/'source02/preparation218.json')
 assert prep['baseline']==base['sources'] and prep['changed']==['nes_rom_loader.sv','nes_rom_spi.sv']
 for n,h in prep['sources'].items():
  if n not in prep['changed']:assert h==base['sources'][n],n
 prep2=read(d/'source02/preparation219.json')
 assert prep2['baseline']==base['sources'] and set(prep2['changed'])=={'nes_rom_loader.sv','nes_rom_spi.sv','nes_spi_boot.sv'}
 for n,h in prep2['sources'].items():
  if n!='nes_spi_boot.sv':assert h==prep['sources'][n],n
 enable=read(d/'enable02/result.json')
 assert enable['passed'] and enable['induction_checks']==1211304 and enable['negative_missing_disable']
 for n,h in enable['sources'].items():assert sha(d/'enable02'/n)==h,n
 for n,h in enable['binding_source_pins'].items():assert sha(BASE/n)==h,n
 for n,h in enable['public_sources'].items():assert sha(ROOT/n)==h,n
 test=read(d/'spi01/result.json');assert test['passed'] and test['same_edge'] and test['retire_checks']==327680
 assert test['source_sha256']==sha(d/'source01/nes_rom_spi.sv') and test['reference_sha256']==sha(old/'source02/nes_rom_spi.sv')
 for n,h in test['sources'].items():assert sha(d/'spi01'/n)==h,n
 for n,h in test['public_sources'].items():assert sha(ROOT/n)==h,n
 assert (d/'spi01/candidate.sv').read_text()==(d/'source01/nes_rom_spi.sv').read_text()
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:assert sha(d/'spi01'/n)==sha(d/'source01'/n),n
 counter=read(d/'counter01/result.json');assert counter['passed'] and counter['negative_wrong_state'] and counter['negative_stop']
 assert counter['script_sha256']==sha(ROOT/'tools/test_nes_counter219.py')
 for n,h in counter['source_pins'].items():assert sha(BASE/n)==h,n
 reused={}
 for name,path in [('epoch217',BASE/'probes/nes-loader217/epoch04/result.json'),('wait216',BASE/'probes/nes-wait216/fixed02/result.json'),('slot216',BASE/'probes/nes-wait216/slot-fixed02/result.json'),('guards216',BASE/'probes/nes-wait216/guards03/result.json')]:
  assert read(path)['passed'];reused[name]=dict(result_sha256=sha(path),path=str(path.relative_to(BASE)))
 common=['nes_wait216_paths','nes_epoch217_paths','nes_control218_paths','nes_payload218_paths','nes_finish218_paths']
 for folder,toolset in [('paths01',common),('paths02',['nes_fault219_paths']),('paths03',common+['nes_fault219_paths']),('paths04',['nes_snapshot219_paths'])]:
  for tool in toolset:
   assert (d/folder/(tool+'.exitcode')).read_text()=='0'
   assert sha(d/folder/(tool+'.tcl'))==sha(ROOT/'tools'/(tool+'.tcl'))
 r=dict(evidence_consistent=True,functional_pass=True,hardware_trial_ready=False,adopted=False,new_package=False,new_arm=False,new_asm=False,
  selected=['source02','counter01','spi01','enable02','mapfit02','timing02','io02','paths03','paths04'],candidates=boards,board=board,spi=test,counter=counter,enable=enable,
  reused_not_rerun=reused,physical=False,fps=None,prior_archives=[verify_archive('nes-boundary218')],
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_retire219.py','tools/test_nes_retire219.py','tools/test_nes_counter219.py','tools/nes_enable219.py','tools/test_nes_enable219.py','tools/nes_fault219_paths.tcl','tools/nes_snapshot219_paths.tcl','tools/nes_retire219_evidence.py','docs/nes-retire219-contract.ko.md']},
  targeted_reports={str(f.relative_to(d)):sha(f) for p in ['paths01','paths02','paths03','paths04'] for f in (d/p).glob('*.rpt')},
  next='Source02 is a functional continuation candidate, not a timing improvement/adoption. Inspect same-edge status snapshot flags/redundant boot masks and RECEIVE qualification jointly, preserving SPI capture/shift and reset/fault priority. Whole-board gates before ARM/current212 ROM paired ASM/ZIP; no clock/SDC relaxation or seed-only fits.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(ROOT/'analysis/retire219-verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(functional=True,timing=board['related_timing_passed'],le=board['fitted_le'],ff=board['registers'],lab=board['lab'],m9k=board['m9k'],setup=board['timing']['implementation']['setup']['slack'],conditional_io=io['conditional_data_bounds_pass'],new_package=False)))
if __name__=='__main__':main()
