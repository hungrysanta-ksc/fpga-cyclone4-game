# SPDX-License-Identifier: MIT
"""Reconcile physical476 return and distinguish receiver improvement from cadence."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--raw',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
names={k:f'nes-{k}-nrom476.txt' for k in ['progress','budget','game-last']}
raw={k:(args.raw/n).read_text(encoding='utf8') for k,n in names.items()}
last=dict(x.split('=',1) for x in raw['game-last'].splitlines() if '=' in x)
fields=dict(x.split('=',1) for x in raw['budget'].splitlines() if '=' in x)
for key,value in {'candidate':'NES-NROM476','board_observed_hex':'78','loaded_bytes':'393216','compared_bytes':'393216','verified':'1','verify_error':'0','start_sent':'1','run_passed':'1','run_error':'0','run_first_error':'0','run_stop_error':'0','stop_ok':'1','base_restored':'1','safe_to_reload':'1','menu_state':'PREPARED_RESET_HELD','native_result':'1','native_receiver_error':'0','native_video_error':'0','trace_aborts':'0','native_sink_error':'2','plan_error':'0'}.items():
 assert last[key]==value,(key,last[key])
for key,value in {'cost_schema':'474','cost_clock_hz':'84000000','cost_counter_available':'1','cost_scene_crc32_hex':'0fddf31c','cost_crc_errors':'0','cost_transfer_stops':'0','failed_transfers':'0','cost_quiet_budget_us':'128'}.items():
 assert fields[key]==value,(key,fields[key])
records=[(int(m[1]),m[2],int(m[3])) for m in re.finditer(r'NROM476 seq=(\d+) stage=(\S+).*?elapsed_ms=(\d+)',raw['progress'])]
assert [x[0] for x in records]==list(range(78)) and records[-1][1]=='MENU_PREPARED'
assert all(a[2]<=b[2] for a,b in zip(records,records[1:]))
marks={stage:ms for seq,stage,ms in records}
seconds=(marks['DISPLAY_STOPPED']-marks['DISPLAY_NEXT'])/1000
n=int(last['native_frames']);assert seconds>0 and n>0
columns=fields['columns'].split(',');bins=[]
for match in re.finditer(r'^b(\d+)=(.*)$',raw['budget'],re.M):
 values=[int(x,16) for x in match[2].split(',')];assert len(values)==len(columns)==23
 bins.append({'index':int(match[1]),**dict(zip(columns,values))})
assert [x['index'] for x in bins]==list(range(12))
totals={k:(max if k=='maxgap' else sum)(x[k] for x in bins) for k in columns}
assert totals['frames']==n and totals['plan']==totals['planner_ticks']+totals['begin_ticks']+totals['finish_ticks']
tick_diff={k:totals[k]-int(last['profile_'+v+'_ticks']) for k,v in [('recv','receive'),('plan','build_stage'),('seal','seal_ack')]}
assert all(abs(x)<=1 for x in tick_diff.values())
clock,spi=84000000,2625000
def bucket(key,name):
 calls,count,hi,lo,maximum=map(int,fields[key].split(','));cycles=(hi<<32)|lo
 return {'name':name,'calls':calls,'calls_per_display':calls/n,'bytes':count,'cycles':cycles,'mean_ms':cycles/clock*1000/n,'maximum_interval_ms':maximum/clock*1000,'ideal_wire_ms':count*8/spi*1000/n}
ops=[bucket(f'cost_op_{i:02d}',name) for i,name in enumerate(fields['cost_op_order'].split(','))]
phases=[bucket(f'cost_phase_{i:02d}',name) for i,name in enumerate(['receive','plan','seal'])]
waits=[]
for i,name in enumerate(fields['cost_poll_order'].split(',')):
 calls,progress,quiet,hi,lo,maximum=map(int,fields[f'cost_poll_{i}'].split(','));assert calls==progress+quiet
 waits.append({'name':name,'valid_calls':calls,'progress_or_complete':progress,'quiet_attempts':quiet,'completed_quiet_cycles':(hi<<32)|lo,'mean_quiet_ms':((hi<<32)|lo)/clock*1000/n,'max_completed_quiet_us':maximum/clock*1e6})
for index,key in [(4,'e0'),(5,'e1'),(6,'e8'),(7,'e9'),(8,'other')]:assert ops[index]['bytes']==totals[key],key
assert sum(x['bytes'] for x in ops[:4])==totals['ingress']
assert sum(totals[k] for k in ['ingress','e0','e1','e8','e9','other'])==int(last['native_wire_bytes'])
assert sum(x['bytes'] for x in ops)==int(last['native_wire_bytes'])+ops[9]['bytes']+ops[10]['bytes']
assert sum(x['calls'] for x in ops)==int(last['native_transactions'])+ops[9]['calls']+ops[10]['calls']
assert ops[11]['calls']==ops[11]['bytes']==0
assert ops[1]['calls']==ops[2]['calls']==10*(n+1)
assert ops[3]['calls']==int(last['trace_commits'])==int(last['trace_ends'])==phases[1]['calls']==n+1
assert ops[8]['calls']==phases[2]['calls']==n
pending=(int(last['sink_window_sent'])-int(last['sink_window_retired']))&65535
assert 1<=pending<=4 and last['sink_window_error']=='2'
assert ops[4]['calls']-sum(x['valid_calls'] for x in waits) in [1,2]
assert int(fields['cost_group_total'])==(n+1)*28
assert int(fields['cost_group_reused'])==(n+1)*27
baseline=json.loads((ROOT/'analysis/nrom475-hardware.json').read_text(encoding='utf8'))
selected=json.loads((ROOT/'analysis/receive476-verification.json').read_text(encoding='utf8'))
package=json.loads((ROOT/'analysis/receive476-package.json').read_text(encoding='utf8'))
assert package['manifest']['FPGA_sha256']==baseline['intended_artifacts']['FPGA_BI3']==selected['artifacts']['FPGA_BI3']
assert package['manifest']['moving_scene_crc32_hex']==fields['cost_scene_crc32_hex']
comparisons=[]
mean_ms=seconds*1000/n
for prior in baseline['runs']:
 p=prior['DWT_inclusive_phases']
 comparisons.append({'baseline_run':prior['run'],'display_speedup_percent':100*((n/seconds)/prior['display']['fps']-1),'mean_ms_saved':prior['display']['mean_ms']-mean_ms,'receive_inclusive_ms_saved':p[0]['mean_ms']-phases[0]['mean_ms'],'seal_inclusive_ms_added':phases[2]['mean_ms']-p[2]['mean_ms'],'plan_inclusive_ms_delta':phases[1]['mean_ms']-p[1]['mean_ms']})
run={'run':1,'input_sha256':{name:hashlib.sha256((args.raw/name).read_bytes()).hexdigest() for name in names.values()},'scene_crc32':fields['cost_scene_crc32_hex'],'display':{'seconds':seconds,'completed':n,'fps':n/seconds,'mean_ms':mean_ms,'bins5s':[x['frames'] for x in bins],'max_gap_ticks10ms':[x['maxgap'] for x in bins]},'DWT_inclusive_phases':phases,'DWT_op_buckets':ops,'quiet_buckets':waits,'coarse_totals':totals,'coarse_profile_tick_disagreement':tick_diff,'comparisons_vs474':comparisons,'group_reuse':{'groups':int(fields['cost_group_total']),'reused':int(fields['cost_group_reused']),'fraction':27/28},'termination':{'runtime_result':1,'deadline_seconds':60,'input_commits':n+1,'completed_EA':n,'cancelled_pending_output_packets':pending,'pending_packets_are_not_frames':True,'sink_error':2,'window_error':2,'STOP_base_menu_ok':True},'progress_ms':marks}
result={'passed':True,'receipt':477,'trial':476,'runs':[run],'intended_artifacts':selected['artifacts'],'user_observation':{'menu_return_normal':True,'new_video_supplied':False},'same_scene_as474':True,'hardware_attestation':'user installation/identity/scene consistent; no on-chip artifact SHA readback','steady_cadence_improved_proven':False,'large_FPS_gain_proven':False,'source_schedule':baseline['source_schedule'],'workload_limits':{'OBJ_rows_in_bins':totals['obj'],'mapdirty_after_first5s':sum(x['mapdirty'] for x in bins[1:]),'same_frame_group_reuse':27/28,'scene_is_gameplay':False,'SMB3_MMC3_validated_on_current_board':False},'conclusions':['Receiver inclusive time falls but SEAL wait rises; about24fps plateau persists','Cold replay39% CPU instruction reduction is not a frame-rate gain','Steady5s bins remain119..121 completions; most added completions occur during startup','Controlled scene remains a regression fixture, not a representative NES or SMB3 performance benchmark','Next gate: same renderer high-diversity/OBJ input plus explicit MMC3/SMB3 board/loader/ROM/area feasibility; do not wait for this pattern to reach60 before game-path work'],'remaining':{'intermediate30fps':False,'sustained60Hz':False,'capture_no_loss_proven':False,'frame_level_p95':None,'whole_CDC_IO_signoff':False,'MMC4_5_proven':False},'no_new_build_or_FIT':True,'scope':__doc__}
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps({'passed':True,'fps':n/seconds,'phases_ms':[x['mean_ms'] for x in phases],'display_speedup_percent':comparisons[0]['display_speedup_percent'],'pending_at_deadline':pending,'OBJ':totals['obj'],'warm_mapdirty':result['workload_limits']['mapdirty_after_first5s']}))
