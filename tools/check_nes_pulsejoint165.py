# SPDX-License-Identifier: MIT
"""Bind latency-aware tests, exact routed inputs and the actual164 MCU caller."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_commandpulse165 import transform
from nes_commandguard165 import transform as guard
from test_nes_commandpulse165 import bench,connected
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from nes_release165 import TARGETS

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test','joint']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes());b=json.loads((a.baseline/'result.json').read_bytes())
 is_payload=m.get('invalid_payload_unobservable',False)
 assert sha(a.baseline/'result.json')==m['baseline_result_sha256'] and m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and set(m['changed'])=={'nes_rom_spi.sv','nes_rom_loader.sv'}
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n not in m['changed']:assert h==m['baseline'][n],n
 assert (d/'nes_rom_spi.sv').read_text()==transform((a.baseline/'nes_rom_spi.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes())
 assert t['passed'] and t['captures']==393741 and t['boundaries']==120 and t['wrong_overlap_rejected'] and not t['same_edge_equivalence']
 assert t['wrong_live_fault_rejected'] and t['wrong_header_rejected'] and t['same_edge_cancellation_checked']
 assert sha(d/'nes_rom_spi.sv')==sha(a.test/'candidate.sv')==t['source_sha256']
 assert sha(a.baseline/'nes_rom_spi.sv')==t['reference_sha256']
 assert (a.test/'capture_tb.sv').read_text()==bench()
 assert (a.test/'tag165_tb.sv').read_text()==connected()
 assert 'PASS COMMANDSTAGE165 wire_frames=219 sck_hz=2625000 ss_gap_ns=2000' in (a.test/'connected.log').read_text()
 for n in ['nes_rom_boot.sv','nes_rom_physical.sv']:assert sha(d/n)==sha(a.test/n)
 assert (d/'nes_rom_loader.sv').read_text()==guard((a.baseline/'nes_rom_loader.sv').read_text())
 old=json.loads((ROOT/'analysis/retirece165-verification.json').read_bytes())
 olddir=a.baseline.parents[1]/'nes-retirece165/map02'
 assert sha(olddir/'result.json')==old['raw_result_sha256']['map02']
 loader=json.loads((olddir/'result.json').read_bytes())['functional_test']
 assert loader['passed'] and loader['states']==294912 and loader['source_sha256']==sha(d/'nes_rom_loader.sv')
 assert sha(d/'nes_rom_loader.sv')==sha(olddir/'nes_rom_loader.sv')
 joint=json.loads((a.joint/'result.json').read_bytes())
 assert joint['passed'] and joint['reference_sha256']==sha(a.baseline/'nes_rom_spi.sv')
 for n,h in joint['sources'].items():assert sha(d/n)==sha(a.joint/n)==h
 assert (a.joint/'tag165_tb.sv').read_text()==connected()
 assert sha(a.joint/'tag165_tb.sv')==joint['bench_sha256']
 assert 'PASS COMMANDSTAGE165 wire_frames=219 sck_hz=2625000 ss_gap_ns=2000' in (a.joint/'connected.log').read_text()
 assert 'edges=1125909 reads=100 acks=7 corruptions=19 cancels=72 overlaps=2' in joint['summary']
 prior=json.loads((ROOT/'analysis/commandstage165-verification.json').read_bytes())
 prior_raw=a.baseline.parents[1]/'nes-commandstage165/map02/result.json'
 assert sha(prior_raw)==prior['raw_result_sha256']['map02']
 assert prior['mcu164']['requested_ss_high_us']==2 and prior['mcu164']['spi_hz']==2625000
 def rows(n):return list(csv.DictReader((d/n).open(),delimiter='\t'))
 paths=rows('commandpulse165-paths.tsv');assert len(paths)==30
 assert {r['target']:r['value'] for r in rows('release165-settings.tsv')}==dict.fromkeys(TARGETS,'ON')
 topology=rows('release165-topology.tsv');chains=rows('release165-paths.tsv');assert len(chains)==15
 for name in ['records','prepared']:
  first=[r for r in topology if r['chain']==name and r['stage']=='0'];assert len(first)==1 and first[0]['to']==first[0]['from'][:-2]+'1]'
 assert all(float(r['slack'])>=0 for r in chains if r['group']!='held')
 public={**prior['public_sources'],**m['public_sources'],**loader['public_sources'],**t['public_sources'],**joint['public_sources'],'tools/check_nes_commandpulse165.py':sha(ROOT/'tools/check_nes_commandpulse165.py'),'tools/check_nes_pulsejoint165.py':sha(Path(__file__))}
 for n in ['tools/nes_commandpayload165.py','tools/test_nes_commandpayload165.py','tools/nes_commandpulse165_paths.tcl','tools/nes_release165_paths.tcl','src/nes/firmware/nes_game149_spi.inc']:
  public[n]=sha(ROOT/n)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 for name in ['commandpulse165','release165']:assert sha(d/(name+'-paths.tcl'))==sha(ROOT/'tools'/('nes_'+name+'_paths.tcl'))
 registers=(d/'commandpulse165-registers.txt').read_text().splitlines();assert len(registers)==6 and len(set(registers))==6
 result={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),'functional_test':loader,'loader_test_reused_from':'retirece165/map02','loader_reused_result_sha256':sha(olddir/'result.json'),'spi_functional_test':t,'spi_unit_test_reused_from':'commandpulse165/test01','joint_functional_test':joint,
  'targeted_ns':{g:{k:min(float(r['slack']) for r in paths if r['group']==g and r['kind']==k) for k in ['setup','hold']} for g in ['failure','length','decode','response','stop']},
  'local_release_chain_setup_hold_pass':True,'source_byte_reproduction':True,'unchanged_files':59,'clock_latency_changed':True,'added_mem_cycles':1,'experimental_spi_identity':0x74,'invalid_payload_unobservable':is_payload,
  'mcu164':prior['mcu164'],'mcu_contract_reused':True,'preapproved_pulses':6,
  'actual_wire_frames':219,'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public,
  'scope':'State-specific guard loader combined with six preapproved pulses; unchanged module unit evidence reused, new joint SPI replay. Pulses keep prior C0/C1/C2 latency and live fault priority; bounded transaction-result comparison, not same-edge equivalence. Actual SPI+boot+READ16 and status wire capture use a model; no MCU full-link, full game, IO/CDC/reset signoff or hardware.'}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','targeted_ns']}))
if __name__=='__main__':main()
