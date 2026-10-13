# SPDX-License-Identifier: MIT
"""Bind destination-state equivalence, new connected replay and routed timing."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_destination165 import transform
from test_nes_state165 import bench
from test_nes_commandpulse165 import connected
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from nes_release165 import TARGETS

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test','joint']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes())
 prior=json.loads((ROOT/'analysis/commandpulse165-verification.json').read_bytes())
 assert sha(a.baseline/'result.json')==prior['raw_result_sha256']['map02']==m['baseline_result_sha256']
 assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and m['changed']==['nes_rom_loader.sv']
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n not in m['changed']:assert h==m['baseline'][n],n
 assert (d/'nes_rom_loader.sv').read_text()==transform((a.baseline/'nes_rom_loader.sv').read_text())
 assert sha(d/'nes_rom_spi.sv')==prior['spi_functional_test']['source_sha256']
 t=json.loads((a.test/'result.json').read_bytes());joint=json.loads((a.joint/'result.json').read_bytes())
 assert t['passed'] and t['states']==294912 and t['sequences']==1056 and t['all_state_codes']==16
 assert t['wrong_stop_rejected'] and t['wrong_unused_rejected']
 assert sha(d/'nes_rom_loader.sv')==sha(a.test/'candidate.sv')==t['source_sha256']
 assert sha(a.baseline/'nes_rom_loader.sv')==t['reference_sha256']
 assert (a.test/'state165_tb.sv').read_text()==bench()
 assert joint['passed'] and joint['reference_sha256']==prior['spi_functional_test']['reference_sha256']
 for n,h in joint['sources'].items():assert sha(d/n)==sha(a.joint/n)==h,n
 assert (a.joint/'tag165_tb.sv').read_text()==connected() and sha(a.joint/'tag165_tb.sv')==joint['bench_sha256']
 assert 'PASS COMMANDSTAGE165 wire_frames=219 sck_hz=2625000 ss_gap_ns=2000' in (a.joint/'connected.log').read_text()
 assert 'edges=1125909 reads=100 acks=7 corruptions=19 cancels=72 overlaps=2' in joint['summary']
 def rows(n):return list(csv.DictReader((d/n).open(),delimiter='\t'))
 assert {r['target']:r['value'] for r in rows('release165-settings.tsv')}==dict.fromkeys(TARGETS,'ON')
 topology=rows('release165-topology.tsv');chains=rows('release165-paths.tsv');assert len(chains)==15
 for name in ['records','prepared']:
  first=[r for r in topology if r['chain']==name and r['stage']=='0'];assert len(first)==1 and first[0]['to']==first[0]['from'][:-2]+'1]'
 assert all(float(r['slack'])>=0 for r in chains if r['group']!='held')
 public={**prior['public_sources'],**m['public_sources'],**t['public_sources'],**joint['public_sources'],'tools/check_nes_destination165.py':sha(Path(__file__))}
 for n in ['tools/nes_destination165_paths.tcl']:public[n]=sha(ROOT/n)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 for name in ['commandpulse165','release165','destination165']:assert sha(d/(name+'-paths.tcl'))==sha(ROOT/'tools'/('nes_'+name+'_paths.tcl'))
 regs=(d/'destination165-registers.txt').read_text().splitlines();assert len(regs)==len(set(regs)) and 1<=len(regs)<=16
 paths=rows('destination165-paths.tsv');assert len(paths)==24
 r={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),'functional_test':t,'joint_functional_test':joint,'spi_unit_test_reused_from':'commandpulse165/test01','mcu164':prior['mcu164'],
 'targeted_ns':{g:{k:min(float(r['slack']) for r in paths if r['group']==g and r['kind']==k) for k in ['setup','hold']} for g in ['begin','fault','timer','error']},
 'physical_state_registers':regs,'source_byte_reproduction':True,'unchanged_files':60,'local_release_chain_setup_hold_pass':True,'added_mem_cycles_over_pulsejoint':0,'experimental_spi_identity':0x74,
 'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public,
 'scope':'New loader destination equations compared over all16 numeric codes and write/reset/STOP sequences; new actual SPI/boot/READ16 composition. Unchanged SPI393741/120/three negatives reused. Not full ROM/game, IO/CDC/reset signoff, MCU or hardware.'}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ['fit_le','used_labs','nominal','targeted_ns','physical_state_registers']}))
if __name__=='__main__':main()
