# SPDX-License-Identifier: MIT
"""Verify218 SPI proof and whole-board gates; never equate consistency with timing."""
from pathlib import Path
import argparse,inspect,json
import nes_board207_evidence as prior
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
from check_nes_boundary165 import measurements

s=inspect.getsource(prior.candidate).replace("suffix=f'{index:02d}';", "suffix=f'{index:02d}';index=2;").replace('preparation207.json','preparation218.json')
s=s.replace("test=read(d/('epoch'+suffix)/'result.json')","test=read(BASE/'probes/nes-board207/epoch02/result.json')")
s=s.replace("d/'epoch02/runner.py'","BASE/'probes/nes-board207/epoch02/runner.py'")
ns=dict(prior.__dict__);exec(compile(s,'candidate218','exec'),ns)

def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-boundary218';old=BASE/'probes/nes-loader217'
 boards={}
 for i in [1,2]:
  io=measurements(d/f'io{i:02d}');(d/f'io{i:02d}/result.json').write_text(json.dumps(io,indent=2)+'\n')
  board,classified=ns['candidate'](d,i);boards[str(i)]=board
  (a.out/f'classified-cdc{i:02d}.json').write_text(json.dumps(classified,indent=2)+'\n')
  board['inherited207_reference_test']=board.pop('functional')
 prep=read(d/'source02/preparation218.json');base=read(old/'source04/preparation217.json')
 assert prep['baseline']==base['sources'] and prep['changed']==['nes_rom_loader.sv','nes_rom_spi.sv']
 for n,h in prep['sources'].items():
  if n not in prep['changed']:assert h==base['sources'][n],n
 test=read(d/'test01/result.json');assert test['passed'] and test['same_edge'] and test['bit_boundaries']==524288
 assert test['source_sha256']==sha(d/'source01/nes_rom_spi.sv') and test['reference_sha256']==sha(old/'source04/nes_rom_spi.sv')
 for n,h in test['sources'].items():assert sha(d/'test01'/n)==h,n
 for n,h in test['public_sources'].items():assert sha(ROOT/n)==h,n
 assert (d/'test01/candidate.sv').read_text()==(d/'source01/nes_rom_spi.sv').read_text()
 assert sha(d/'source01/nes_rom_spi.sv')==sha(d/'source02/nes_rom_spi.sv')
 payload=read(d/'payload02/result.json');assert payload['passed'] and payload['negative_blocked'] and payload['negative_stop']
 assert payload['script_sha256']==sha(ROOT/'tools/test_nes_payload218.py')
 for n,h in payload['source_pins'].items():assert sha(BASE/n)==h,n
 joint=read(d/'joint02/result.json');assert joint['passed'] and joint['script_sha256']==sha(ROOT/'tools/test_nes_boundary218_joint.py')
 for n,h in joint['sources'].items():assert sha(d/'joint02'/n)==h,n
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:assert sha(d/'joint02'/n)==sha(d/'source02'/n),n
 reused={}
 for name,path in [('loader217',old/'test01/result.json'),('epoch217',old/'epoch04/result.json'),('wait216',BASE/'probes/nes-wait216/fixed02/result.json'),('slot216',BASE/'probes/nes-wait216/slot-fixed02/result.json'),('guards216',BASE/'probes/nes-wait216/guards03/result.json')]:
  assert read(path)['passed'];reused[name]=dict(result_sha256=sha(path),path=str(path.relative_to(BASE)))
 for i in [1,2]:
  for tool in ['nes_wait216_paths','nes_epoch217_paths','nes_control218_paths']+(['nes_payload218_paths'] if i==2 else []):
   assert (d/f'paths{i:02d}'/(tool+'.exitcode')).read_text()=='0'
   assert sha(d/f'paths{i:02d}'/(tool+'.tcl'))==sha(ROOT/'tools'/(tool+'.tcl'))
 assert (d/'paths03/nes_finish218_paths.exitcode').read_text()=='0'
 assert sha(d/'paths03/nes_finish218_paths.tcl')==sha(ROOT/'tools/nes_finish218_paths.tcl')
 assert not board['related_timing_passed']
 assert board['timing']['implementation']['setup']['slack']=='-0.437'
 assert board['timing']['nominal']['setup']['slack']=='-0.207'
 r=dict(evidence_consistent=True,functional_pass=True,hardware_trial_ready=False,adopted=False,new_package=False,new_arm=False,new_asm=False,
  selected=['source02','test01','payload02','joint02','mapfit02','timing02','io02','paths02','paths03'],board=board,candidates=boards,spi=test,payload=payload,joint=joint,
  reused_not_rerun=reused,physical=False,fps=None,
  prior_archives=[verify_archive('nes-loader217')],
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_boundary218.py','tools/test_nes_boundary218.py','tools/nes_payload218.py','tools/test_nes_payload218.py','tools/test_nes_boundary218_joint.py','tools/nes_control218_paths.tcl','tools/nes_payload218_paths.tcl','tools/nes_finish218_paths.tcl','tools/nes_boundary218_evidence.py','docs/nes-boundary218-contract.ko.md']},
  targeted_reports={str(f.relative_to(d)):sha(f) for i in [1,2,3] for f in (d/f'paths{i:02d}').glob('*.rpt')},
  targeted_nominal_slack_ns=dict(spi_offset=1.311,payload_capture=1.024,loader_error=.906,serial_gray=1.612,response_retire=.015,count_clear=-.207),
  next='Keep same-edge byte_last and payload capture candidates; jointly resolve response-address equality/error_response -> command_retire pulses (strict5.5ns -0.437, nominal +0.015) and phase[4] -> count_clear -> loaded_bytes (nominal -0.207). Preserve same-edge mismatch cancellation, immutable READ tag, STOP/drain/count semantics. No CE/seed-only loop, clock/SDC waiver or same215/044 repeat. Whole-board gates before new ARM/current212 ROM paired ASM/ZIP and FIRSTLEVELSCROLL.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(ROOT/'analysis/boundary218-verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(functional=True,timing=board['related_timing_passed'],le=board['fitted_le'],ff=board['registers'],lab=board['lab'],m9k=board['m9k'],setup=board['timing']['implementation']['setup']['slack'],conditional_io=io['conditional_data_bounds_pass'],new_package=False)))
if __name__=='__main__':main()
