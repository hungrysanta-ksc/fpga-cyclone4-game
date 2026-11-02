# SPDX-License-Identifier: MIT
"""Compare one saved MMC558 run with the successful MMC551 run."""
import argparse
import json
from pathlib import Path

from analyze_nes_hardware552 import ROOT, inputs, performance


def start_windows(b):
    rows=[dict(zip(b['columns'].split(','),(int(v,16) for v in b[f'b{i:02}'].split(',')),strict=True)) for i in range(12)]
    summary=[]
    for lo,hi in ((1,8),(8,11),(8,9),(9,10),(10,11)):
        part=rows[lo:hi]
        n=sum(r['frames'] for r in part)
        summary.append(dict(start_s=lo*5,end_s=hi*5,frames=n,
            output_ms=10*sum(r['seal'] for r in part)/n,map_rows=sum(r['mapdirty'] for r in part)/n,
            E1_bytes=sum(r['e1'] for r in part)/n))
    return summary


def analyze(raw,reference):
    old=json.loads((ROOT/'analysis/hardware552-mmc551.json').read_bytes())
    result=performance(raw,old,558)
    game,budget,_,_=inputs(raw,558)
    _,previous_budget,_,pins=inputs(reference,551)
    assert pins==old['source_SHA256']
    assert game['run_error']==game['run_stop_error']==game['fault_context_valid']=='0'
    assert game['sink_window_ack']=='1' and budget['cost_phase_and_op_are_nested']=='1'
    periods=[]
    for before,after in zip(old['completion_windows'],result['completion_windows'],strict=True):
        assert (before['start_s'],before['end_s'])==(after['start_s'],after['end_s'])
        periods.append(dict(start_s=after['start_s'],end_s=after['end_s'],
            previous=before['displays'],current=after['displays'],
            delta_pct=100*(after['fps']/before['fps']-1)))
    result.update(trial=558,trial_family='MMC',physical=True,hardware_run_passed=True,
        user_report=dict(starts=2,successful=2,menu_return=True,perception='similar FPS'),
        logged_runs=1,completion_comparison=periods,start_bin_work_per_frame={'551':start_windows(previous_budget),'558':start_windows(budget)},
        trimmed_change_pct=100*(result['trimmed_fps']/old['trimmed_fps']-1),
        phase_delta_ms={k:v['ms_per_display']-old['phases'][k]['ms_per_display'] for k,v in result['phases'].items()},
        termination=dict(runtime_result=1,receiver_error=27,trace_begins=int(game['trace_begins']),
            trace_commits=int(game['trace_commits']),aborts=int(game['trace_aborts']),crc_errors=int(budget['cost_crc_errors']),
            stop_ok=True,base_restored=True,menu_state=game['menu_state']),
        reference='analysis/hardware552-mmc551.json',package='analysis/trial558-package.json')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.raw,a.reference),indent=2)+'\n',encoding='utf8',newline='\n')
