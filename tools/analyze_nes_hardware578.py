# SPDX-License-Identifier: MIT
"""Reconcile MMC577 physical logs; retain incomplete terminal output separately."""
import argparse
import json
import struct
from pathlib import Path
from analyze_nes_hardware552 import ROOT, inputs
from analyze_nes_hardware559 import start_windows
from nes_windows518 import windows, duration_ms
from analyze_nes_supply485_hardware import sha


def analyze(raw):
    g,b,p,pins=inputs(raw,577)
    reference=ROOT/'analysis/hardware559-mmc558.json'
    old=json.loads(reference.read_text(encoding='utf8'))
    for key in ('run_error','run_rom_error','run_stop_error','fault_context_valid',
                'native_receiver_error','native_video_error','plan_error','trace_aborts'):
        assert g[key]=='0',key
    assert g['run_passed']==g['native_result']=='1'
    assert b['boot_reason']=='1' and b['cost_scene_crc32_hex']=='5a04eed7'
    assert b['cost_clock_hz']=='84000000' and b['cost_counter_available']=='1'
    assert b['cost_phase_and_op_are_nested']=='1'
    assert all(b[k]=='0' for k in ('cost_crc_errors','cost_transfer_stops','failed_transfers'))
    n=int(g['native_frames']);elapsed=duration_ms(p)
    split=windows((raw/'nes-budget-mmc577.txt').read_text(encoding='utf-8-sig'),elapsed)
    phases={}
    for i,name in enumerate(('receive','plan_supply','output_final_ack')):
        calls,_,hi,lo,maximum=map(int,b[f'cost_phase_{i:02}'].split(','))
        phases[name]=dict(calls=calls,ms_per_display=((hi<<32)+lo)*1000/84000000/n)
    commits=int(g['trace_commits']);ea=int(b['cost_op_08'].split(',')[0])
    assert commits==int(g['trace_ends'])==int(g['trace_begins'])==n+1
    assert ea==n==phases['output_final_ack']['calls']
    assert int(g['profile_last_display_tick'])==5996 and b['open']=='1'
    pending=(int(g['sink_window_sent'])-int(g['sink_window_retired']))&65535
    assert pending==1
    assert (g['native_sink_error'],g['sink_window_error'],g['sink_trace_ack_valid'],
            g['sink_trace_mismatch_hex'])==('2','3','0','00')
    request=bytes.fromhex(g['sink_trace_request_hex'])
    assert len(request)==16 and request[:2]==bytes([2,2])
    assert struct.unpack_from('<I',request,4)[0]==n+1
    assert struct.unpack_from('<H',request,8)[0]==int(g['trace_generation'])
    assert bytes.fromhex(g['sink_trace_ack_hex'])==bytes(12)
    columns=b['columns'].split(',')
    rows=[dict(zip(columns,(int(v,16) for v in b[f'b{i:02}'].split(',')),strict=True))
          for i in range(12)]
    assert sum(r['frames'] for r in rows)==n
    bins=[dict(start_s=i*5,displays=r['frames'],max_gap_ms=10*r['maxgap'])
          for i,r in enumerate(rows)]
    periods=[]
    for before,after in zip(old['completion_windows'],split,strict=True):
        assert (before['start_s'],before['end_s'])==(after['start_s'],after['end_s'])
        periods.append(dict(**after,previous_displays=before['displays'],
                            previous_fps=before['fps'],delta_pct=100*(after['fps']/before['fps']-1)))
    work=start_windows(b)
    matched=[]
    for lo,hi in ((5,40),(40,55),(5,55)):
        counts=[sum(r['displays'] for r in src if lo<=r['start_s']<hi)
                for src in (old['frame_start_bins'],bins)]
        matched.append(dict(start_s=lo,end_s=hi,old=counts[0],new=counts[1]))
    trimmed=sum(r['displays'] for r in split)/50
    return dict(trial=577,trial_family='MMC',physical=True,hardware_run_passed=True,
        logged_runs=1,user_report=dict(menu_return=True,perception='FPS felt improved'),
        source_SHA256=pins,reference='analysis/hardware559-mmc558.json',
        reference_SHA256=sha(reference),package='analysis/trial577-package.json',
        display=dict(completed=n,seconds=elapsed/1000,fps=n*1000/elapsed,mean_ms=elapsed/n),
        completion_windows=split,completion_comparison=periods,trimmed_fps=trimmed,
        trimmed_change_pct=100*(trimmed/old['trimmed_fps']-1),
        frame_start_bins=bins,matched_start_bins=matched,
        start_bin_work_per_frame={'558':old['start_bin_work_per_frame']['558'],'577':work},
        phases=phases,phase_delta_ms={k:v['ms_per_display']-old['phases'][k]['ms_per_display']
                                    for k,v in phases.items()},
        terminal=dict(runtime_result=1,commits=commits,retires_EA=ea,pending=pending,
            request_hex=request.hex(),request_kind=2,section=2,serial=n+1,
            window_error=3,sink_error=2,receiver_error=0,video_error=0,
            last_display_s=59.96,stop_ok=True,base_restored=True,menu_state=g['menu_state'],
            interpretation='Consistent with transfer/post-transfer deadline during unfinished ordinary output; physical failing instruction not recorded. Not a blanket waiver for window error 3.'),
        boot=dict(polls=int(b['boot_polls']),ticks=int(b['boot_ticks'])),
        limitations=['One unsynchronized playthrough per comparison; not an isolated causal speedup.',
                     'Start bins are not completion bins or scene identities; maxgap is a 10ms quantized maximum, not p95.',
                     'DWT phases include IRQ and wait; polling and operation costs overlap those phases.',
                     'No per-frame DMA/VBlank split, capture-loss rate or full electrical IO sign-off.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=analyze(a.raw)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:result[k] for k in ('display','completion_comparison','phases','phase_delta_ms')}))
