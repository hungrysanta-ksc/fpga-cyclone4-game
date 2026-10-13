# SPDX-License-Identifier: MIT
"""Pin transformed RTL, boundary tests and actual routed state/capture paths."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_directstate165 import loader,physical
from test_nes_directloader165 import bench as loader_bench
from test_nes_directreader165 import bench as reader_bench
from test_nes_directjoint165 import connected
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from nes_release165 import TARGETS

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','loader','reader','joint','pins']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes())
 prior=json.loads((ROOT/'analysis/update165-verification.json').read_bytes())
 assert sha(a.baseline/'result.json')==prior['raw_result_sha256']['map03']==m['baseline_result_sha256']
 assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and set(m['changed'])=={'nes_rom_loader.sv','nes_rom_physical.sv'}
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n not in m['changed']:assert h==m['baseline'][n],n
 assert (d/'nes_rom_loader.sv').read_text()==loader((a.baseline/'nes_rom_loader.sv').read_text())
 assert (d/'nes_rom_physical.sv').read_text()==physical((a.baseline/'nes_rom_physical.sv').read_text())
 t=json.loads((a.loader/'result.json').read_bytes());rd=json.loads((a.reader/'result.json').read_bytes())
 joint=json.loads((a.joint/'result.json').read_bytes());pins=json.loads((a.pins/'result.json').read_bytes())
 assert all(x['passed'] for x in [t,rd,joint,pins])
 assert t['states']==294912 and t['sequences']==1056 and t['all_state_codes']==16
 for flag in ['wrong_stop_rejected','wrong_unused_rejected','onehot_invariant_checked','terminal_invariant_checked']:assert t[flag],flag
 assert sha(d/'nes_rom_loader.sv')==sha(a.loader/'candidate.sv')==t['source_sha256']
 assert sha(a.baseline/'nes_rom_loader.sv')==t['reference_sha256']
 assert (a.loader/'state165_tb.sv').read_text()==loader_bench()
 assert rd['cases']==5 and rd['reads']==120 and rd['cancels']==126 and rd['stopped_resets']==5
 assert rd['wrong_capture_rejected'] and rd['capture_invariant_checked']
 assert sha(d/'nes_rom_physical.sv')==sha(a.reader/'candidate.sv')==rd['source_sha256']
 assert sha(a.baseline/'nes_rom_physical.sv')==rd['reference_sha256']
 assert (a.reader/'reader_last165_tb.sv').read_text()==reader_bench()
 assert (a.joint/'tag165_tb.sv').read_text()==connected()
 assert joint['spi_unit_reuse_sha256']==sha(a.baseline/'result.json') and joint['spi_unit_captures']==393741
 for n,h in joint['sources'].items():assert sha(d/n)==sha(a.joint/n)==h,n
 assert 'PASS COMMANDSTAGE165 wire_frames=219 sck_hz=2625000 ss_gap_ns=2000' in (a.joint/'connected.log').read_text()
 assert 'edges=1125909 reads=100 acks=7 corruptions=19 cancels=72 overlaps=2' in joint['sequential_summary']
 assert len(pins['cases'])==16 and pins['negative110_rejected'] and pins['negative_hold_rejected']
 assert pins['read_cycles']==16 and pins['normal_access_ns']==70
 assert sha(d/'nes_rom_physical.sv')==sha(a.pins/'nes_rom_physical.sv')==pins['sources']['nes_rom_physical.sv']
 assert sha(a.pins/'executed-driver.py')==sha(ROOT/'tools/test_nes_screen141_reader.py')
 for n,h in pins['sources'].items():assert sha(a.pins/n)==h,n
 def rows(n):return list(csv.DictReader((d/n).open(),delimiter='\t'))
 assert {r['target']:r['value'] for r in rows('release165-settings.tsv')}==dict.fromkeys(TARGETS,'ON')
 topology=rows('release165-topology.tsv');chains=rows('release165-paths.tsv');assert len(chains)==15
 for name in ['records','prepared']:
  first=[r for r in topology if r['chain']==name and r['stage']=='0'];assert len(first)==1 and first[0]['to']==first[0]['from'][:-2]+'1]'
 assert all(float(r['slack'])>=0 for r in chains if r['group']!='held')
 public={**prior['public_sources'],**m['public_sources'],**t['public_sources'],**rd['public_sources'],**joint['public_sources']}
 for n in ['tools/check_nes_directstate165.py','tools/nes_directstate165_paths.tcl','tools/test_nes_screen141_reader.py','tests/nes-functional/rom_physical_model.sv','tests/nes-functional/rom_physical_tb.sv','tests/nes-functional/safe122_monitor.svh','tests/nes-functional/cdc125_reader.svh']:public[n]=sha(ROOT/n)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 for name in ['release165','commandpulse165','directstate165']:assert sha(d/(name+'-paths.tcl'))==sha(ROOT/'tools'/('nes_'+name+'_paths.tcl'))
 regs=rows('directstate165-registers.tsv')
 phase=[r['name'] for r in regs if r['group']=='phase'];captures=[r['name'] for r in regs if r['group']=='capture']
 # FAILED only feeds its own bit and the numeric test view, so it is pruned.
 assert {x.rsplit('|',1)[1] for x in phase}=={f'phase[{i}]' for i in [0,1,2,3,4,5,7,8]},regs
 assert len(captures)==2 and not [r for r in regs if r['group']=='oldstate'],regs
 paths=rows('directstate165-paths.tsv');assert len(paths)==54
 r={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),'functional_test':t,'reader_test':rd,'joint_functional_test':joint,'reader_pin_test':pins,'mcu164':prior['mcu164'],
 'targeted_ns':{g:{k:min(float(x['slack']) for x in paths if x['group']==g and x['kind']==k) for k in ['setup','hold']} for g in ['state','error','begin','fault','reader','prediction','command','address','counter']},
 'physical_state_registers':phase,'local_capture_registers':captures,'source_byte_reproduction':True,'unchanged_files':59,'local_release_chain_setup_hold_pass':True,'added_mem_cycles_over_update':0,'experimental_spi_identity':0x74,
 'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public,
 'scope':'New explicit-state loader294912/1056/all16codes, reader5cases120reads126cancels5stopped resets, actualSPI boot READ16 and reader16phase70ns pin monitors. Numeric unused9..15 state semantics verified in RTL; reset-zero unused bits and unobserved FAILED bit optimized out physically. No new latency. Unchanged SPI unit/MCUgap reused. Not IO/CDC board signoff, MCU/full ROM/game or hardware.'}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ['fit_le','used_labs','nominal','targeted_ns','physical_state_registers','local_capture_registers']}))
if __name__=='__main__':main()
