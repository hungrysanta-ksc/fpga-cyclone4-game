# SPDX-License-Identifier: MIT
"""Bind passive403 observations to exact402 whole MAP and ARM/ROM schedule."""
import argparse,collections,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_joint400 import image,timing
from analyze_nes_scope403 import budget,schedule

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'analysis/scope403-verification.json');a=p.parse_args();d=BASE/'probes/nes-scope403';run=d/'trace01';base=BASE/'probes/nes-joint402/live04';pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return sha(q)
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 bm=js(base/'manifest402.json');m=js(run/'manifest403.json');assert m['RTL']==bm['RTL']and m['passive_trace403']
 for n,h in m['RTL'].items():assert pin(run/n)==h==pin(base/n)==pin(BASE/'probes/nes-joint402/map07'/n)
 assert pin(run/'program398.hex')==pin(base/'program398.hex')
 assert pin(run/'sink.hex')==pin(base/'sink.hex')and image(run/'output.elf')==image(base/'output.elf');pin(run/'output.elf');pin(base/'output.elf')
 assert pin(run/'executed-worker367.py')==pin(base/'executed-worker367.py')
 monitor=read(ROOT/'tests/nes-control399/ports.svh').replace('ports399.csv','ports403.csv').replace('capture&&!dut.flow.read359[33]','capture&&dut.flow.read_pending')+read(ROOT/'tests/nes-scope403/extra.svh')
 tb=read(base/'joint266_tb.sv');at=tb.rindex('endmodule');assert read(run/'joint266_tb.sv')==tb[:at]+monitor+tb[at:]
 assert m['test']==pin(run/'joint266_tb.sv')and m['base402_test']==pin(base/'joint266_tb.sv')
 vlog=read(run/'vlog.log');command=next(x for x in vlog.splitlines()if x.startswith('vlog -sv '));assert set(command.split()[2:])==set(m['RTL'])|{'joint266_tb.sv'}
 log=read(run/'vsim.log');assert 'PASS REFILL267 frames=12'in log and 'CADENCE367 attempts=10 admitted=10 missed=0'in log and not re.search(r'^# \*\* Fatal:',log,re.M)
 # Passive tracing must not change any recorded event or actual ARM cost.
 assert pin(run/'joint-events.csv')==pin(base/'joint-events.csv')
 arm=js(run/'arm-result.json');old_arm=js(base/'arm-result.json');assert arm==old_arm and arm['passed']
 t=timing(list(csv.reader(read(run/'joint-events.csv').splitlines())));assert all(x['accepted']for x in t['captures'])and len(t['captures'])==10
 rom=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+) input_requests=(\d+) input_replies=(\d+) input_pending=(\d+)',log);assert rom and list(map(int,rom.groups()))==[71964,71964,0,17378,17378,0]
 pin(run/'extra403.csv');extra=[];polls={};actions=[]
 with(run/'extra403.csv').open(newline='',encoding='utf8')as file:
  for x in csv.reader(file):
   if x[0]=='io':
    if x[3]=='0':
     k=(int(x[1]),int(x[2]));v=polls.setdefault(k,dict(frame=k[0],address=k[1],reads=0,first_ps=int(x[-1]),last_ps=0));v['reads']+=1;v['last_ps']=int(x[-1])
    else:actions.append(dict(frame=int(x[1]),address=int(x[2]),PC=int(x[4]),prior_token=int(x[5]),length=int(x[6]),ms=int(x[-1])/1e9))
   elif x[0]not in('lease','snapshot_change'):extra.append(x)
 ports=list(csv.reader(read(run/'ports403.csv').splitlines()))
 H={f:{int(x[2]):int(x[3])for x in extra if x[:2]==['host',str(f)]}for f in range(905,917)}
 N={f:{int(x[2]):int(x[3])for x in extra if x[:2]==['NES',str(f)]}for f in range(905,917)}
 spi=[dict(command=int(x[1]),transactions=int(x[2]),post_command_live_key_change_transactions=int(x[3]))for x in extra if x[0]=='SPI'and int(x[1])in(224,225,226,232,233)]
 minimum_header=int(next(x[1]for x in extra if x[0]=='minimum_header_host_clocks'));minimum_palette=int(next(x[1]for x in extra if x[0]=='minimum_palette_sample_NES_clocks'))
 IO={f:[dict(address=int(x[2]),fires=int(x[3]),wait_clocks=int(x[4]))for x in extra if x[:2]==['IO',str(f)]and(int(x[3])or int(x[4]))]for f in range(905,917)}
 context={f:[dict(address=int(x[2]),reads=int(x[3]),writes=int(x[4]))for x in extra if x[:2]==['context',str(f)]and(int(x[3])or int(x[4]))]for f in range(905,917)}
 read_events=sum(int(x[3])for x in ports if x[0]=='host_count'and x[2]=='1');assert read_events==25462
 shape=js(d/'ram01/result.json');assert shape['passed']and not shape['whole_MAP']and not shape['pipeline_function_verified'];assert pin(d/'ram01/ram_shape403.sv')==shape['source']==pin(ROOT/'tests/nes-scope403/ram_shape.sv')and pin(d/'ram01/output_files/shape.map.rpt')==shape['report']
 whole=budget();assert whole['whole']==js(ROOT/'analysis/joint402-cost.json')['funded402']['whole']
 saved=js(ROOT/'analysis/scope403-budget.json');assert saved['scopes']==whole['scopes']and saved['baseline402_schedule']==schedule()
 layout=saved['RAM_plan']['host_layout'];addresses=[a for v in layout for a in range(v['first'],v['last']+1)];assert addresses==list(range(800,1024))
 spec=js(ROOT/'docs/nes-scope403-plan.json');pin(ROOT/'docs/nes-scope403-contract.ko.md')
 assert spec['design_caps_not_measured']['new_total_excluding_retained_palette384FF']==whole['scopes']['plus_compact_fetch_patch_frame']['new_caps_total']
 assert spec['design_caps_not_measured']['new_control_comb_cap']==whole['new_control_comb_cap_for1172']==802
 assert [(v['command'],v['transactions'],v['post_command_live_key_change_transactions'])for v in spi]==[(225,349,142),(226,762,123),(233,50,50)]
 assert minimum_header==31 and minimum_palette==4 and N[915][2]==691240
 for q in(BASE/'probes/nes-joint402/map07/output_files/board.map.rpt',BASE/'probes/nes-joint402/map07/output_files/board.map.summary',BASE/'probes/nes-joint402/map07/result.json'):pin(q)
 report=dict(audit_passed=True,scope=__doc__,exact402_recorded_events=True,exact402_ARM_result=True,exact402_RTL_program_image=True,whole_Lite=whole['whole'],new_RTL=False,new_ARM=False,new_whole_MAP=False,new_controller_area=None,new_time_gain_ms=None,time_goal=False,area_goal=False,FIT=False,STA=False,physical60fps=False,hardware_ready=False,host_counts=H,NES_counts=N,IO_counts=IO,context_address_counts=context,SPI_snapshot=spi,minimum_header_host_clocks=minimum_header,minimum_palette_sample_NES_clocks=minimum_palette,read_events=read_events,actual_ARM=dict(instructions=sum(v['instructions']for v in arm['frames']),SPI_bytes=sum(v['SPI_bytes']for v in arm['frames']),component_stack=arm['stack_observed'],full_RUN=False,hardware_cycles=False),schedule=schedule(),scope_budget=whole,RAM_shape=shape,service_design_budget=dict(header_internal_host_clocks=8,uninterruptible_microstep_host_clocks=2,payload_byte_host_clocks=8,not_measured_replacement=True),pins=pins)
 report['host_counter_names']=['ordinary_write','tile_copy_write','binding','prefill_read','bind_read','bind_capture','ordinary_plus_context_grant','tag_write_demand','tag_grant','tag_wait','plan_payload_write','context_plus_plan_write','live_key_change_clocks_including_precommand_NOT_used_as_frozen_snapshot_count','simultaneous_prefill_commit_and_consume','open_wait','put_wait']
 report['NES_counter_names']=['capture_and_old_display','armed_and_old_display','materialized_and_old_display','committed_and_old_display','raster_line_start','raster_midline_sample','palette_copy','row_commit','midline_palette_difference']
 report['SPI_count_scope']='Only response-bearing commands after command byte. Precommand command0 changes are excluded.'
 report['IO_read_poll_spans']=list(polls.values());report['IO_write_actions']=actions
 report['IO_poll_span_is_not_exclusive_work_time']=True
 report['counter_frame_is_foreground_display_frame_not_capture_identity']=True
 report['capture917_is_start_admission_not_complete917_display']=True
 report['hot_path_check']=dict(min_palette_sample_ns=minimum_palette*46.561,bytewise192bit_compare_host_clocks=24,bytewise_compare_ns=24*1000/84,bytewise_fits_even_without_other_work=24*1000/84<=minimum_palette*46.561,header_budget_host_clocks=8,observed_min_header_host_clocks=minimum_header)
 for q in sorted((ROOT/'tools').glob('*403*.py'))+sorted((ROOT/'tests/nes-scope403').glob('*')):pin(q)
 a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps(dict(passed=True,pins=len(pins),minimum_header_host_clocks=minimum_header,minimum_palette_sample_NES_clocks=minimum_palette,SPI_snapshot=spi),ensure_ascii=False))
if __name__=='__main__':main()
