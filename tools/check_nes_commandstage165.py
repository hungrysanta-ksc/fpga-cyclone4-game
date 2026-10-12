# SPDX-License-Identifier: MIT
"""Bind latency-aware tests, exact routed inputs and the actual164 MCU caller."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_commandstage165 import transform
from nes_commandpayload165 import transform as payload
from test_nes_commandstage165 import bench,connected
from test_nes_commandpayload165 import bench as payload_bench
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from nes_release165 import TARGETS

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced','test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes());b=json.loads((a.baseline/'result.json').read_bytes())
 is_payload=m.get('invalid_payload_unobservable',False)
 assert sha(a.baseline/'result.json')==m['baseline_result_sha256'] and m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and m['changed']==['nes_rom_spi.sv']
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n!='nes_rom_spi.sv':assert h==m['baseline'][n],n
 assert (d/'nes_rom_spi.sv').read_text()==(payload if is_payload else transform)((a.baseline/'nes_rom_spi.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes())
 assert t['passed'] and t['captures']==393741 and t['boundaries']==120 and t['wrong_overlap_rejected'] and not t['same_edge_equivalence']
 assert sha(d/'nes_rom_spi.sv')==sha(a.test/'candidate.sv')==t['source_sha256']
 assert sha(a.baseline/'nes_rom_spi.sv')==t['reference_sha256']
 assert (a.test/'capture_tb.sv').read_text()==(payload_bench if is_payload else bench)()
 assert (a.test/'tag165_tb.sv').read_text()==connected()
 assert 'PASS COMMANDSTAGE165 wire_frames=219 sck_hz=2625000 ss_gap_ns=2000' in (a.test/'connected.log').read_text()
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:assert sha(d/n)==sha(a.test/n)
 e=a.baseline.parents[1]/'nes-game164/evidence';v=json.loads((ROOT/'analysis/game164-verification.json').read_bytes())
 assert sha(e/'manifest.json')==v['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 files=['nes_game149_spi.inc','nes_h1_stm32.c','nes_rom_spi.c','nes_rom_verify.c','stm32f4xx/timer.c','stm32f4xx/clock.c']
 evidence={}
 for n in files:
  rel='arm/src/'+n;assert sha(e/rel)==pins[rel],rel;evidence[n]=sha(e/rel)
 engine=(e/'arm/src/nes_game149_spi.inc').read_text();caller=(e/'arm/src/nes_h1_stm32.c').read_text()
 assert sha(e/'arm/src/nes_game149_spi.inc')==sha(ROOT/'src/nes/firmware/nes_game149_spi.inc')
 assert 'io->select(io->ctx,false);io->wait_us(io->ctx,2);' in engine
 assert 'io->select(io->ctx,true);io->wait_us(io->ctx,2);' in engine
 assert 'SPI_CR1_SSI|(4u<<SPI_CR1_BR_Pos)' in engine and 'CONFIG_CPU_FREQUENCY != 84000000' in engine
 assert 'rx[1]!=0x6b' in caller and '(void)ctx;delay_us(duration);' in caller
 timer=(e/'arm/src/stm32f4xx/timer.c').read_text()
 assert 'if(nes_diag_active()){(void)nes_return_delay(time,false);return;}' in timer
 assert '(CONFIG_CPU_FREQUENCY/(milliseconds?1000u:1000000u))*time' in timer
 assert 'RCC_CFGR_PPRE1_DIV2' in (e/'arm/src/stm32f4xx/clock.c').read_text()
 def rows(n):return list(csv.DictReader((d/n).open(),delimiter='\t'))
 paths=rows('commandstage165-paths.tsv');assert len(paths)==30
 assert {r['target']:r['value'] for r in rows('release165-settings.tsv')}==dict.fromkeys(TARGETS,'ON')
 topology=rows('release165-topology.tsv');chains=rows('release165-paths.tsv');assert len(chains)==15
 for name in ['records','prepared']:
  first=[r for r in topology if r['chain']==name and r['stage']=='0'];assert len(first)==1 and first[0]['to']==first[0]['from'][:-2]+'1]'
 assert all(float(r['slack'])>=0 for r in chains if r['group']!='held')
 public={**b['public_sources'],**m['public_sources'],**t['public_sources'],'tools/check_nes_commandstage165.py':sha(Path(__file__))}
 for n in ['tools/nes_commandpayload165.py','tools/test_nes_commandpayload165.py','tools/nes_commandstage165_paths.tcl','tools/nes_release165_paths.tcl','src/nes/firmware/nes_game149_spi.inc']:
  public[n]=sha(ROOT/n)
 for n,h in public.items():assert sha(ROOT/n)==h,n
 for name in ['commandstage165','release165']:assert sha(d/(name+'-paths.tcl'))==sha(ROOT/'tools'/('nes_'+name+'_paths.tcl'))
 result={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),'functional_test':b['functional_test'],'spi_functional_test':t,
  'targeted_ns':{g:{k:min(float(r['slack']) for r in paths if r['group']==g and r['kind']==k) for k in ['setup','hold']} for g in ['failure','length','decode','eligibility','stop']},
  'local_release_chain_setup_hold_pass':True,'source_byte_reproduction':True,'unchanged_files':60,'clock_latency_changed':True,'added_mem_cycles':1,'experimental_spi_identity':0x74,'invalid_payload_unobservable':is_payload,
  'mcu164':dict(source_sha256=evidence,manifest_sha256=sha(e/'manifest.json'),spi_hz=2625000,requested_ss_high_us=2,requested_ss_to_sck_us=2,old_reply_identity=0x6b,old_firmware_must_not_run_candidate=True,physical_gap_measured=False),
  'actual_wire_frames':219,'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public,
  'scope':'Capture/decode/retire adds one mem_clk; bounded transaction-result comparison, not same-edge equivalence. Actual SPI+boot+READ16 and status wire capture use a model; no MCU full-link, full game, IO/CDC/reset signoff or hardware.'}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','targeted_ns']}))
if __name__=='__main__':main()
