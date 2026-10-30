# SPDX-License-Identifier: MIT
"""Read482/485/489/492 physical DWT/driver counters without hardcoding frame totals.

Phase, driver-op and quiet counters are nested. No same-scene claim is inferred
from using the same ROM; menu visibility still requires the user's observation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fields=lambda s:{k:v.strip() for k,v in re.findall(r'^([a-zA-Z0-9_]+)=(.*?)\s*$',s,re.M)}


def analyse(folder,trial):
    paths={k:folder/f'nes-{k}-mmc{trial}.txt' for k in ['progress','budget','game-last']}
    raw={k:q.read_text(encoding='utf-8-sig').replace('\0','') for k,q in paths.items()}
    g,b=fields(raw['game-last']),fields(raw['budget'])
    expected={'candidate':f'NES-MMC{trial}','board_expected_hex':'7b','board_observed_hex':'7b','board_seen':'1',
              'load_result':'0','file_result':'0','loaded_bytes':'393216','compared_bytes':'393216','verified':'1',
              'verify_error':'0','start_sent':'1','run_passed':'1','run_error':'0','run_first_error':'0','run_stop_error':'0',
              'run_rom_error':'0','native_receiver_error':'0','native_result':'1',
              'stop_ok':'1','base_restored':'1','safe_to_reload':'1','menu_state':'PREPARED_RESET_HELD'}
    for k,v in expected.items():assert g[k]==v,(trial,k,g.get(k))
    # A deadline inside the resident OBJ writer propagates through slot()==
    # UINT16_MAX to planner error13. This is not sufficient evidence of OBJ
    # capacity exhaustion: require the exact preceding deadline/plan-guard
    # signature, zero transport/receiver errors and a committed unfinished frame.
    video=int(g['native_video_error'])
    deadline_OBJ=(video==13 and g['native_result']=='1' and g['plan_error']=='2' and
                  g['native_sink_error']=='0' and g['sink_window_error']=='0' and
                  g['trace_aborts']=='0' and g['plan_end']=='0' and
                  int(g['trace_commits'])==int(g['native_frames'])+1)
    #489 can hit the same runtime deadline at the explicit zero-slot plan
    # callback, which reports14 instead of the resident OBJ slot's13. Keep
    # this exact terminal signature trial-specific; never waive code14 alone.
    deadline_plan=(trial in (489,492) and video==14 and g['native_result']=='1' and
                   g['plan_error']=='2' and g['native_sink_error']=='0' and
                   g['sink_window_error']=='0' and g['trace_aborts']=='0' and
                   g['plan_end']=='0' and g['plan_sent']=='0' and
                   g['fault_context_valid']=='0' and
                   int(g['trace_begins'])==int(g['trace_ends'])==int(g['trace_commits'])==int(g['native_frames'])+1)
    assert video==0 or deadline_OBJ or deadline_plan,('unexpected video failure',video)
    for k,v in {'cost_schema':'474','cost_counter_available':'1','cost_clock_hz':'84000000',
                'cost_scene_crc32_hex':'5a04eed7','cost_crc_errors':'0','failed_transfers':'0'}.items():
        assert b[k]==v,(trial,k,b.get(k))
    records=[(int(i),stage,int(ms)) for i,stage,ms in re.findall(rf'MMC{trial} seq=(\d+) stage=(\S+).*?elapsed_ms=(\d+)',raw['progress'])]
    assert records and all(a[0]<z[0] and a[2]<=z[2] for a,z in zip(records,records[1:]))
    marks={stage:ms for _,stage,ms in records}
    seconds=(marks['DISPLAY_STOPPED']-marks['DISPLAY_NEXT'])/1000
    n=int(g['native_frames']);assert n>0 and seconds>0
    def bucket(key):
        calls,size,hi,lo,maximum=map(int,b[key].split(','));cycles=(hi<<32)|lo
        return {'calls':calls,'bytes':size,'cycles':cycles,'ms_per_completed_display':cycles/84000/n,
                'max_interval_ms':maximum/84000}
    phases={name:bucket(f'cost_phase_{i:02d}') for i,name in enumerate(['receive','plan_supply','seal_final_ACK'])}
    ops={name:bucket(f'cost_op_{i:02d}') for i,name in enumerate(b['cost_op_order'].split(','))}
    quiet={}
    for i,name in enumerate(['CREDIT_including485_plan_wait','DRAIN','FINAL_ACK']):
        calls,progress,waits,hi,lo,maximum=map(int,b[f'cost_poll_{i}'].split(','));cycles=(hi<<32)|lo
        quiet[name]={'calls':calls,'progress':progress,'quiet':waits,'cycles':cycles,
                     'ms_per_completed_display':cycles/84000/n,'max_interval_ms':maximum/84000}
    columns=b['columns'].split(',');bins=[]
    for i,line in re.findall(r'^b(\d+)=(.*)$',raw['budget'],re.M):
        values=[int(x,16) for x in line.split(',')];assert len(values)==len(columns)
        bins.append({'index':int(i),**dict(zip(columns,values))})
    assert [v['index'] for v in bins]==list(range(12)) and sum(v['frames'] for v in bins)==n
    sent,retired=int(g['sink_window_sent']),int(g['sink_window_retired'])
    return {'trial':trial,'hardware_run_passed':True,
            'termination_class':('deadline_during_plan_emit_signature' if deadline_plan else
                                 'deadline_during_OBJ_emit' if deadline_OBJ else 'deadline'),
            'last_incomplete_frame_displayed':False,
            'display':{'completed':n,'seconds':seconds,'fps':n/seconds,
            'mean_ms':1000*seconds/n},'DWT_phases_nested':phases,'driver_ops_nested':ops,
            'quiet_nested':quiet,
            'E1_observation':{'driver_calls':ops['E1']['calls'],'software_sent16':sent,'software_retired16':retired,
                              'driver_minus_sent_mod16':(ops['E1']['calls']-sent)&65535,
                              'physical_queue_empty_proven':False,
                              'note':'A post-transfer deadline can leave a physical E1 uncounted by software. Matching sent/retired does not prove physical acceptance/retirement of the last write.'},
            'wire_bytes':sum(v['bytes'] for v in ops.values()),'bins':bins,'source_SHA256':{q.name:sha(q) for q in paths.values()},
            'terminal_state':{k:v for k,v in g.items() if k.startswith(('native_','plan_','sink_window_'))},
            'menu_visible_user_confirmation_required':True,'same_scene_proven':False,
            'note':'DWT includes actual IRQ/guard/wait. Finite-run averages may include an unfinished final frame; op/quiet counters are nested, not extra time.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--trial',type=int,choices=[482,485,489,492],default=485);p.add_argument('--baseline-raw',type=Path)
    p.add_argument('--baseline-trial',type=int,choices=[482,485,489,492],default=482)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    r=analyse(a.raw,a.trial)
    if a.baseline_raw:
        old=analyse(a.baseline_raw,a.baseline_trial);r[f'baseline{a.baseline_trial}']=old
        r['observed_mean_delta_ms']=r['display']['mean_ms']-old['display']['mean_ms']
        r['same_scene_speedup_claim']=False
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(r['display']))
