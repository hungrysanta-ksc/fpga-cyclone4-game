# SPDX-License-Identifier: MIT
"""Same-artifact SMB3 capture/M4 and MMC3 whole-board feasibility ledger."""
import argparse,csv,hashlib,json,re,statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def summary(path):
 s=path.read_text(encoding='utf8')
 def value(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s)[1].replace(',',''))
 return {'LE':value('Total logic elements'),'comb':value('Total combinational functions'),'FF':value('Dedicated logic registers'),'RAM_bits':value('Total memory bits')}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['m4','board','baseline','out']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();m=json.loads((a.m4/'result.json').read_text(encoding='utf8'));prep=json.loads((a.board/'mmc478-preparation.json').read_text(encoding='utf8'))
 assert m['passed'] and len(m['frames'])==71
 assert m['candidate_firmware']==json.loads((ROOT/'analysis/receive476-verification.json').read_text())['artifacts']['firmware_stm']
 for x in m['frames']:
  assert x['baseline']['state_sha256']==x['candidate']['state_sha256']
  assert x['baseline']['source_SPI_calls']==x['candidate']['source_SPI_calls']
  assert x['baseline']['planner_instructions']==x['candidate']['planner_instructions']
 assert 'Successful' in (a.board/'output_files/board.map.summary').read_text()
 assert 'Successful' in (a.board/'output_files/board.fit.summary').read_text()
 for name,digest in prep['base_inputs'].items():
  if name not in prep['changed']:assert sha(a.board/name)==digest,name
 for key in ['changed','original_auto_found_dependencies','original_transitive_SDC_dependencies']:
  for name,digest in prep[key].items():assert sha(a.board/name)==digest,name
 timing={}
 for view in ['implementation','nominal']:
  rows=list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(),delimiter='\t'));selected={}
  for kind in ['setup','hold']:
   related=[x for x in rows if x['kind']==kind and ((x['from_clock']=='nes')==(x['to_clock']=='nes'))]
   selected[kind]=min(related,key=lambda x:float(x['slack']))
  timing[view]=selected
 def stats(values):return {'min':min(values),'median':statistics.median(values),'max':max(values)}
 rows=m['frames'];profile={'frames':71,'frames_ID':[905,975],'source':'pinned nes-delta231/test07 geometry/raw, no new game run','host_encoder':'current2232 formats; accepted and independently compared to active canonical arrays, NOT byte-identical real FPGA SPI proof','generation':'assigned905..975, epoch1/serial1..71, synthetic positive SPI/plan/DMA completion','payload_bytes':stats([x['payload'] for x in rows]),'OBJ_count':stats([x['counts'][2] for x in rows]),'raw_bytes':stats([x['raw_bytes'] for x in rows]),'tiles':stats([x['candidate']['tiles'] for x in rows]),'receive_instructions_baseline':stats([x['baseline']['receive_instructions'] for x in rows]),'receive_instructions476':stats([x['candidate']['receive_instructions'] for x in rows]),'receive_reduction_percent':stats([100*(1-x['candidate']['receive_instructions']/x['baseline']['receive_instructions']) for x in rows]),'planner_instructions':stats([x['candidate']['planner_instructions'] for x in rows]),'same_receiver_video_resident_and_plan_bytes':True,'plan_callback_count':stats([x['plan_count'] for x in rows]),'NROM474_warm_planner_instructions':172546,'planner_median_ratio_vs_NROM_example':statistics.median(x['candidate']['planner_instructions'] for x in rows)/172546,'instruction_counts_are_not_hardware_cycles_or_FPS':True}
 old_map=summary(a.baseline/'output_files/board.map.summary');new_map=summary(a.board/'output_files/board.map.summary');old_fit=summary(a.baseline/'output_files/board.fit.summary');new_fit=summary(a.board/'output_files/board.fit.summary')
 rpt=(a.board/'output_files/board.sta.summary').read_text();raw={kind:min(float(x) for x in re.findall(r'Type\s*:[^\n]*\b'+kind+r'\b[^\n]*\nSlack\s*:\s*(-?[\d.]+)',rpt)) for kind in ['Setup','Recovery']}
 result={'passed':True,'scope':__doc__,'M4':profile,'M4_firmware_sha256':{'baseline474':m['baseline_firmware'],'candidate476':m['candidate_firmware']},'capture_input_sha256':m['input_sha256'],'palette_sha256':m['palette_sha256'],'MMC3':{'base_QSF_inputs':prep['base_inputs'],'restored_cart':prep['changed'],'auto_found_dependencies_now_pinned':prep['original_auto_found_dependencies'],'transitive_SDC_now_pinned':prep['original_transitive_SDC_dependencies'],'QSF_sha256':sha(a.board/'board.qsf'),'MAP_reference':old_map,'MAP_candidate':new_map,'MAP_delta':{k:new_map[k]-old_map[k] for k in old_map},'FIT_reference':old_fit,'FIT_candidate':new_fit,'FIT_delta':{k:new_fit[k]-old_fit[k] for k in old_fit},'device_LE':15408,'arithmetic_remaining_LE':15408-new_fit['LE'],'related_timing':timing,'raw_STA_min_ns':raw,'functional_game_test':False,'ARM_loader_still_NROM_only':True,'status_ID_still78_NOT_safe_game_profile':True,'new_bitstream_or_installer_built':False,'hardware_use_approved':False,'whole_CDC_IO_signoff':False},'limits':[m['limits'],'same-frame repeated NROM is not representative; actual same-game FPS remains unmeasured','FIT and related setup/hold passing do not approve reset/CDC/IO or a game boot','no source tile/ROM IRQ competition or actual65816 game workload bound yet'],'failures_preserved':['m4game01 missing anonymous-union DWARF member in harness; m4game02 noncanonical bool ABI parameter; repaired03','map01 omitted existing auto-discovered CIRAM dependency; not a mapper logic failure','fit02 lacked transitive cdc181.sdc, so failed before placement; NOT capacity failure','map03/fit03 use original exact dependencies and unchanged seed/constraints; no optimization/seed search'],'raw':'probes/nes-game478/m4game03 and mmc03','next':['typed MMC3 profile identity and exact SMB3 loader/CRC/readback/START/STOP binding','actual mapper+source/query and input/display ROM arbitration with original game snapshots','same-game 65816/observer/menu and timing/IO gates before any hardware package'],'scripts':{n:sha(ROOT/'tools'/n) for n in ['check_nes_game478.py','prepare_nes_mmc478.py','analyze_nes_game478.py']}}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({'passed':True,'M4_frames':71,'planner_median':profile['planner_instructions']['median'],'FIT':new_fit,'remaining_LE':15408-new_fit['LE'],'related_setup_hold_ns':{v:{k:float(x['slack']) for k,x in d.items()} for v,d in timing.items()},'game_hardware_approved':False}))
