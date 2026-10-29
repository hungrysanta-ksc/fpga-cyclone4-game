# SPDX-License-Identifier: MIT
"""Same-scene physical471/474 comparison from two preserved474 returns."""
import argparse,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
baseline=json.loads((ROOT/'analysis/nrom473-hardware.json').read_text(encoding='utf8'))
package=json.loads((ROOT/'analysis/nrom474-package.json').read_text(encoding='utf8'))
selected=json.loads((ROOT/'analysis/nrom474-verification.json').read_text(encoding='utf8'))
assert baseline['scene']['crc32']==package['manifest']['moving_scene_crc32_hex']=='0fddf31c'
assert baseline['intended_artifacts']['FPGA_sha256']==package['manifest']['FPGA_sha256']==selected['artifacts']['FPGA_BI3']
clock,spi=84000000,2625000;runs=[]
for run in [1,2]:
 names={k:f'nes-{k}-nrom474-{run}회차.txt' for k in ['progress','budget','game-last']}
 data={k:(a.raw/n).read_text(encoding='utf8') for k,n in names.items()}
 last=dict(s.split('=',1) for s in data['game-last'].splitlines() if '=' in s)
 fields=dict(s.split('=',1) for s in data['budget'].splitlines() if '=' in s)
 for k,v in {'candidate':'NES-NROM474','board_observed_hex':'78','loaded_bytes':'393216','compared_bytes':'393216','verified':'1','verify_error':'0','start_sent':'1','run_passed':'1','run_error':'0','run_first_error':'0','run_stop_error':'0','stop_ok':'1','base_restored':'1','safe_to_reload':'1','native_result':'1','native_receiver_error':'0','native_video_error':'0','trace_aborts':'0','native_sink_error':'2'}.items():assert last[k]==v,(run,k,last[k])
 for k,v in {'cost_schema':'474','cost_clock_hz':str(clock),'cost_counter_available':'1','cost_scene_crc32_hex':'0fddf31c','cost_crc_errors':'0','cost_transfer_stops':'0','failed_transfers':'0','cost_quiet_budget_us':'128'}.items():assert fields[k]==v,(run,k,fields[k])
 progress=[(int(m[1]),m[2],int(m[3])) for m in re.finditer(r'NROM474 seq=(\d+) stage=(\S+).*?elapsed_ms=(\d+)',data['progress'])]
 assert [v[0] for v in progress]==list(range(78)) and all(x[2]<=y[2] for x,y in zip(progress,progress[1:]))
 marks={v[1]:v[2] for v in progress};assert progress[-1][1]=='MENU_PREPARED'
 seconds=(marks['DISPLAY_STOPPED']-marks['DISPLAY_NEXT'])/1000;n=int(last['native_frames']);assert seconds==60.07 and n==1417
 columns=fields['columns'].split(',');bins=[]
 for m in re.finditer(r'^b(\d+)=(.*)$',data['budget'],re.M):
  values=[int(x,16) for x in m[2].split(',')];assert len(values)==len(columns)==23
  bins.append({'index':int(m[1]),**dict(zip(columns,values))})
 assert [v['index'] for v in bins]==list(range(12))
 total={k:(max if k=='maxgap' else sum)(v[k] for v in bins) for k in columns}
 assert total['frames']==n and total['plan']==total['planner_ticks']+total['begin_ticks']+total['finish_ticks']
 profile_disagreement={k:total[k]-int(last['profile_'+f+'_ticks']) for k,f in [('recv','receive'),('plan','build_stage'),('seal','seal_ack')]}
 assert all(abs(v)<=1 for v in profile_disagreement.values())
 def bucket(key,name):
  calls,count,hi,lo,maximum=map(int,fields[key].split(','));cycles=(hi<<32)|lo
  return {'name':name,'calls':calls,'calls_per_display':calls/n,'bytes':count,'cycles':cycles,'mean_ms':cycles/clock*1000/n,'maximum_interval_ms':maximum/clock*1000,'ideal_wire_ms':count*8/spi*1000/n}
 ops=[bucket('cost_op_'+f'{i:02d}',name) for i,name in enumerate(fields['cost_op_order'].split(','))]
 phases=[bucket('cost_phase_'+f'{i:02d}',name) for i,name in enumerate(['receive','plan','seal'])]
 waits=[]
 for i,name in enumerate(fields['cost_poll_order'].split(',')):
  calls,progress_count,quiet,hi,lo,maximum=map(int,fields[f'cost_poll_{i}'].split(','));assert calls==progress_count+quiet
  waits.append({'name':name,'valid_calls':calls,'progress_or_complete':progress_count,'quiet_attempts':quiet,'completed_quiet_cycles':(hi<<32)|lo,'mean_quiet_ms':((hi<<32)|lo)/clock*1000/n,'max_completed_quiet_us':maximum/clock*1e6})
 assert ops[11]['calls']==ops[11]['bytes']==0
 for index,key in [(4,'e0'),(5,'e1'),(6,'e8'),(7,'e9'),(8,'other')]:assert ops[index]['bytes']==total[key],(run,key)
 assert sum(v['bytes'] for v in ops[:4])==total['ingress']
 assert sum(total[k] for k in ['ingress','e0','e1','e8','e9','other'])==int(last['native_wire_bytes'])
 assert sum(v['bytes'] for v in ops)==int(last['native_wire_bytes'])+ops[9]['bytes']+ops[10]['bytes']
 assert sum(v['calls'] for v in ops)==int(last['native_transactions'])+ops[9]['calls']+ops[10]['calls']
 assert ops[1]['calls']==ops[2]['calls']==10*(n+1)
 assert ops[3]['calls']==int(last['trace_commits'])==int(last['trace_ends'])==phases[1]['calls']==n+1
 assert ops[8]['calls']==phases[2]['calls']==n
 assert int(last['sink_window_sent'])-int(last['sink_window_retired'])==1 and last['sink_window_error'] in ['2','3']
 assert ops[4]['calls']-sum(v['valid_calls'] for v in waits) in [1,2]
 groups,reused=int(fields['cost_group_total']),int(fields['cost_group_reused']);assert groups==(n+1)*28 and reused==(n+1)*27
 quiet_ms=sum(v['mean_quiet_ms'] for v in waits)
 runs.append({'run':run,'input_sha256':{n:sha(a.raw/n) for n in names.values()},'scene_crc32':fields['cost_scene_crc32_hex'],
  'display':{'seconds':seconds,'completed':n,'fps':n/seconds,'mean_ms':seconds*1000/n,'bins5s':[v['frames'] for v in bins],'max_gap_ticks10ms':[v['maxgap'] for v in bins]},
  'DWT_inclusive_phases':phases,'DWT_op_buckets':ops,'quiet_buckets':waits,
  'group_reuse':{'groups':groups,'reused':reused,'fraction':reused/groups},
  'totals':{'all_wrapped_SPI_ms':sum(v['mean_ms'] for v in ops),'all_wire_lower_bound_ms':sum(v['ideal_wire_ms'] for v in ops),'quiet_mean_ms':quiet_ms,'E0_plus_quiet_ms':ops[4]['mean_ms']+quiet_ms,'quiet_and_E0_disjoint_but_auxiliary_SPI_can_overlap_quiet':True,'outside_recorded_complete_phases_ms':seconds*1000/n-sum(v['mean_ms'] for v in phases)},
  'receive_no_payload_polls':phases[0]['calls']-ops[1]['calls']-ops[3]['calls'],
  'coarse_profile_tick_disagreement':profile_disagreement,'coarse_totals':total,
  'termination':{'first_result':'6000tick deadline','sink_error':int(last['native_sink_error']),'window_error':int(last['sink_window_error']),'last_pending_output':1,'completed_EA_retire':ops[8]['calls'],'STOP_base_reload_ok':True,'menu_prepared_ms':marks['MENU_PREPARED']},'progress_ms':marks})
for r in runs:
 r['comparison_vs471']={'same_scene_speedup_percent':100*(r['display']['fps']/baseline['display']['mean_fps']-1),'mean_time_reduction_percent':100*(1-r['display']['mean_ms']/baseline['display']['mean_ms']),'plan_reduction_percent':100*(1-r['DWT_inclusive_phases'][1]['mean_ms']/baseline['DWT_phases_inclusive'][1]['mean_ms_per_display']),'remaining_mean_ms_to30fps':r['display']['mean_ms']-1000/30,'remaining_mean_ms_to60fps':r['display']['mean_ms']-1000/60}
# Source-proven overlap already exists; do not label a historical feature as new.
board=BASE/'probes/nes-nrom471/validation01/board-source'
source_files=['nes_capture_lease201.sv','nes_native_frame201.sv','nes_native_export203.sv','nes_live_joint.sv']
source_pins={n:sha(board/n) for n in source_files}
for n,h in source_pins.items():assert selected['FPGA_inputs'][n]==h,n
lease=(board/source_files[0]).read_text();frame=(board/source_files[1]).read_text();top=(board/source_files[3]).read_text()
assert 'assign export_permitted=!reset&&!stop&&!fault&&!lost&&!waiting_display;' in lease
assert 'assign release_frame=stop||export_release||fault||lost||bad_retire;' in lease
assert 'scanline==7 && dot==257' in frame and '.enable(export_permitted204&&!direct_nes_fault204)' in top
result={'passed':True,'receipt':475,'trial':474,'limited_two_run_pass':True,'same_scene_physical_speedup_observed':True,
 'intended_artifacts':selected['artifacts'],'artifact_note':'identity/scene and user installation consistent; no on-chip firmware/bitstream hash attestation',
 'user_observation':{'two_executions':True,'same_visual_behavior_as471':True,'normal_menu_return':True,'new_video_supplied':False},
 'baseline471':{'display':baseline['display'],'phases':baseline['DWT_phases_inclusive'],'E0':baseline['DWT_op_buckets'][4],'receive_no_payload_polls':baseline['DWT_phases_inclusive'][0]['calls']-baseline['DWT_op_buckets'][1]['calls']-baseline['DWT_op_buckets'][3]['calls']},
 'runs':runs,'source_schedule':{'pins':source_pins,'capture_export_overlap_already_present':True,'capture_boundary':'NES scanline7/dot257 when not owned or active','next_collector_can_restart_after_export_commit':True,'next_export_waits_for_old_display_lease_retire':True,'hardware_boundary_timestamps_available':False},
 'conclusions':['same moving scene completion rate19.610454->23.589146fps in both runs; observed20.29% improvement',
 'planner phase13.629809->6.085214/6.068296ms confirms physical compute-path benefit; combined build cannot isolate causal share exactly',
 'E0 call reductions are not equal to latency savings: quiet waiting and D0 no-payload polling replace part of the time',
 'two run receive/seal phase redistribution with identical1417 completions suggests scheduling/phase dependence; exact NES/SNES/VBlank attribution unmeasured',
 'source capture/export already overlaps one following frame; preserve ownership instead of claiming this as a new optimization',
 'next: profile remaining ARM receive/CRC work and record capture-ready/export-ready/SEAL/finalACK on one timeline before any ownership or ABI change'],
 'remaining':{'intermediate30fps':False,'sustained60Hz':False,'capture_no_loss_proven':False,'pixel_exact_new_video_proven':False,'frame_level_p95':None,'whole_CDC_IO_signoff':False,'MMC4_5_proven':False},
 'no_new_build_or_FIT':True,'FPGA_cost_unchanged':selected['FPGA_resources'],'ARM_budget_unchanged':selected['device_budget'],
 'scope':__doc__}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':True,'both_fps':[r['display']['fps'] for r in runs],'speedup_percent':runs[0]['comparison_vs471']['same_scene_speedup_percent'],'plan_ms':[r['DWT_inclusive_phases'][1]['mean_ms'] for r in runs],'quiet_ms':[r['totals']['quiet_mean_ms'] for r in runs],'receive_empty_polls':[r['receive_no_payload_polls'] for r in runs]}))
