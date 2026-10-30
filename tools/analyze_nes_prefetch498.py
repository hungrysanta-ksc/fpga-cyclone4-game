# SPDX-License-Identifier: MIT
"""498 reproducible scope/cost ledger; no physical FPS inference."""
import argparse,json,re
from pathlib import Path
from nes_status495 import ROOT,sha
from analyze_nes_status495 import timing
from check_nes_supply485_arm import ELFFile

def load(p):return json.loads(p.read_text(encoding='utf8'))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['board','arm','arm-test','candidate','boundary','loader-proof','live','prepared','local','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prior=load(ROOT/'analysis/status495-verification.json');recipe=load(a.candidate/'result.json')
 inputs=dict(prior['FPGA']['whole_board_inputs'])
 for n,d in recipe['changed_board'].items():inputs[n]=d['after']
 for n,h in inputs.items():assert sha(a.board/n)==h,n
 assert sha(a.arm/'nes_native_runtime165.c')==recipe['ARM_patch']
 summary=(a.board/'output_files/board.fit.summary').read_text();assert 'Fitter Status : Successful' in summary
 def value(label):return int(re.search(re.escape(label)+r' : ([\d,]+)',summary)[1].replace(',',''))
 le=value('Total logic elements');comb=value('Total combinational functions');ff=value('Dedicated logic registers');ram=value('Total memory bits')
 m9k=int(re.search(r'; M9Ks\s*; (\d+) /',(a.board/'output_files/board.fit.rpt').read_bytes().decode('latin1'))[1])
 firmware=a.arm/'obj-nes-100/firmware.stm';size=firmware.stat().st_size
 arm=load(a.arm_test/'result.json');identity=load(a.local/'identity03.json');boundary=load(a.boundary/'result.json');loader=load(a.loader_proof/'result.json');live=load(a.live/'result.json') if (a.live/'result.json').is_file() else None
 assert all(x['passed'] for x in [arm,identity,boundary]);assert arm['firmware_sha256']==sha(firmware)
 assert boundary['sha256']['nes_live_joint.sv']==sha(a.board/'nes_live_joint.sv')
 assert loader['passed'] and loader['candidate_SHA256']==sha(a.board/'nes_rom_loader.sv')
 assert sha(a.live/'nes_native_runtime165.c')==recipe['ARM_patch']
 # The two-frame join uses the same board before the loader-only truth-table
 # rewrite. Bind that exact difference; do not silently equate two builds.
 differing=[n for n,h in inputs.items() if (a.live/n).is_file() and sha(a.live/n)!=h]
 assert differing==['nes_rom_loader.sv'],differing
 assert sha(a.live/'nes_rom_loader.sv')==loader['baseline_SHA256']
 harness=['host.c','native_fixture.inc','nes_native_runtime165.c','join208_tb.sv']
 for n in harness:assert sha(a.live/n)==sha(a.prepared/n),n
 assert "consumer['commits']==2" in a.prepared.with_name(a.prepared.name+'-runner.py').read_text()
 with (a.arm/'obj-nes-100/sd2snes.elf').open('rb')as f:
  sections=[s for s in ELFFile(f).iter_sections()if s['sh_flags']&2]
  text=sum(s['sh_size']for s in sections if not s['sh_flags']&1)
  data=sum(s['sh_size']for s in sections if s['sh_flags']&1 and s['sh_type']!='SHT_NOBITS')
  bss=sum(s['sh_size']for s in sections if s['sh_type']=='SHT_NOBITS')
 times=timing(a.board)
 result={'candidate':'prefetch498 experimental','selected_for_hardware':False,'new_installer':False,'physical_baseline':'MMC4939.57fps','physical_FPS':None,'full_path_acceleration_proven':False,
 'recipe':recipe,'ARM':{'firmware_SHA256':sha(firmware),'firmware_B':size,'Flash_free_B':212992-size,'text_B':text,'data_B':data,'BSS_B':bss,'RUN_workspace_B':31848,'new_global_RAM_B':0,'wait498_static_stack_B':24,'runtime_step_static_stack_B':56,'isolated_callback_observed_stack_B':max(x['isolated_callback_observed_stack_B']for x in arm['rows']),'full_nested_stack_IRQ_proof':False},
 'FPGA':{'whole_board_inputs':inputs,'LE':le,'LE_remaining':15408-le,'comb':comb,'FF':ff,'RAM_bits':ram,'M9K':m9k,'delta_vs495':{'LE':le-15121,'comb':comb-14097,'FF':ff-8394,'RAM_bits':ram-264800},'delta_vs493':{'LE':le-15272,'comb':comb-14078,'FF':ff-8392,'RAM_bits':ram-264800},'related_timing_ns':times,'related_timing_passed':all(v>=0 for row in times.values()for v in row.values()),'full_reset_CDC_IO_signoff':False,'SNES_program_unchanged':inputs['sink-program.hex']==prior['FPGA']['whole_board_inputs']['sink-program.hex']},
 'linked_ARM_receive':arm,'linked_ARM_identity_retire':identity,'RTL_boundary':boundary,'loader_equivalence':loader,'joint':live,'joint_board_difference_from_cost_build':differing,
 'joint_common_M4_IRQ_clock':False,'new_total_frame_ms':None,'new_final_display_speedup_ms':None,
 'limits':['Host C/RTL/65816 RPC is functional,not common physical ARM/IRQ time','Early receive is charged inside SEAL;old receive/SEAL phases are no longer comparable','No added payload compression or assumed reduction in SPI bytes','No hardware menu/continuous FPS claim','Full reset/CDC/IO and nested IRQ stack remain open']}
 result['joint_functional_passed']=bool(live and live.get('passed'))
 result['rejected_variants']={
  'candidate03_board02':{'continuous_drain_gate':True,'related_timing_ns':timing(a.board.parent/'nes-prefetch498-board02'),'joint_failure':'generation13 exporter error1/ABORT and prior lease fault;no completed display'},
  'candidate04_board03':{'external_busy_hold':True,'related_timing_ns':timing(a.board.parent/'nes-prefetch498-board03'),'selected':False},
  'candidate05_board04':{'start_only_gate':True,'joint_functional_passed':bool(live and live.get('passed')),'related_timing_ns':timing(a.board.parent/'nes-prefetch498-board04'),'selected_for_hardware':False}}
 result['local_evidence_selectors']={'recipe':'candidate06','ARM':'arm01/test04/identity03','boundary':'boundary03','loader':'loader01','joint':'live04/postcheck01','whole':'board05/whole07/timing05'}
 result['joint_workload']='Fixed MMC3 fixture,not a first-level SMB3 gameplay or sustained FPS trial'
 result['fixed_postcheck_generator_matches_executed_harness']={n:sha(a.live/n)for n in harness}
 result['bounded_tests_and_related_timing_passed']=result['joint_functional_passed'] and result['FPGA']['related_timing_passed']
 result['source_SHA256']={p.name:sha(p)for p in (ROOT/'tools').glob('*prefetch498*.py')}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({'joint':result['joint_functional_passed'],'FPGA':{k:v for k,v in result['FPGA'].items()if k!='whole_board_inputs'},'Flash_free_B':212992-size}))
