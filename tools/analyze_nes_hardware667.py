"""Compare MMC666 physical completion windows and work bins with MMC662."""
import argparse
import json
import re
import struct
from pathlib import Path
from analyze_nes_hardware552 import inputs
from analyze_nes_hardware663 import work
from check_nes_fault641 import ROOT, digest, evidence
from decode_nes_minreject180 import decode
from nes_windows518 import windows, duration_ms


def analyze(raw,baseline):
    old=evidence('hardware663-mmc662.json')
    g,b,p,pins=inputs(raw,666)
    _,bb,_,oldpins=inputs(baseline,662)
    assert oldpins==old['source_SHA256']
    for k in ('run_error','run_rom_error','run_first_error','run_stop_error',
              'fault_context_valid','native_receiver_error','plan_error','trace_aborts'):
        assert g[k]=='0',k
    assert g['run_passed']==g['native_result']=='1'
    assert b['boot_reason']=='1' and b['plan_valid']=='0'
    assert all(b[k]=='0' for k in ('failed_transfers','cost_crc_errors','cost_transfer_stops'))
    assert b['cost_scene_crc32_hex']=='5a04eed7' and b['cost_clock_hz']=='84000000'
    assert b['cost_phase_and_op_are_nested']==b['cost_cycles_include_IRQ_guard_and_wait']=='1'
    n=int(g['native_frames']);elapsed=duration_ms(p)
    split=windows((raw/'nes-budget-mmc666.txt').read_text(encoding='utf-8-sig'),elapsed)
    comparison=[dict(**c,previous_displays=o['displays'],previous_fps=o['fps'],
                     delta_pct=100*(c['fps']/o['fps']-1)) for c,o in zip(split,old['completion_windows'],strict=True)]
    trimmed=sum(r['displays'] for r in split)/50
    phases={}
    for i,k in enumerate(('receive','plan_supply','output_final_ack')):
        calls,_,hi,lo,maximum=map(int,b[f'cost_phase_{i:02}'].split(','))
        phases[k]=dict(calls=calls,ms_per_display=((hi<<32)+lo)/84000/n,max_ms=maximum/84000)
    assert phases['output_final_ack']['calls']==n
    rows,current_work=work(b);_,old_work=work(bb)
    assert sum(r['frames'] for r in rows)==n
    workload=[]
    for c,o in zip(current_work,old_work,strict=True):
        workload.append(dict(start_s=c['start_s'],end_s=c['end_s'],
                             per_frame_change_pct={k:100*(v/o['per_frame'][k]-1) for k,v in c['per_frame'].items()},
                             output_start_bin_change_pct=100*(c['output_ms']/o['output_ms']-1)))
    commits=int(g['trace_commits']);ea=int(b['cost_op_08'].split(',')[0])
    assert commits==int(g['trace_begins'])==int(g['trace_ends'])==n+1 and ea==n
    pending=(int(g['sink_window_sent'])-int(g['sink_window_retired']))&65535
    assert pending==1 and b['open']=='1'
    assert (g['native_sink_error'],g['sink_window_error'],g['native_video_error'],g['sink_trace_ack_valid'],g['sink_trace_mismatch_hex'])==('2','3','7','0','00')
    req=bytes.fromhex(g['sink_trace_request_hex'])
    assert len(req)==16 and req[:2]==bytes((2,2)) and bytes.fromhex(g['sink_trace_ack_hex'])==bytes(12)
    serial,generation,offset,length=struct.unpack_from('<IHHH',req,4)
    assert serial==n+1 and generation==int(g['trace_generation'])==int(g['native_generation'])+1
    history=decode((raw/'nes-game-last-mmc666.txt').read_text(encoding='utf-8-sig'))
    events=history['events']
    assert len(events)==8 and [e['event'] for e in events]==['REJECT','RECOVERY']*4
    assert all(e['errors']==0 for e in events)
    marks=[(stage,int(t)) for stage,t in re.findall(r'stage=(\w+).*?elapsed_ms=(\d+)',p)]
    assert marks[-1][0]=='MENU_PREPARED'
    at=dict(marks)
    return dict(trial=666,trial_family='MMC',physical=True,hardware_run_passed=True,logged_runs=1,
                user_report=dict(start_success=True,menu_return=True,route='similar first level to MMC662',perception='FPS felt improved'),
                source_SHA256=pins,reference='analysis/hardware663-mmc662.json',reference_SHA256=digest(ROOT/'analysis/hardware663-mmc662.json'),
                package='analysis/trial666-package.json',package_SHA256=digest(ROOT/'analysis/trial666-package.json'),
                display=dict(completed=n,seconds=elapsed/1000,fps=n*1000/elapsed,mean_ms=elapsed/n),
                completion_windows=split,completion_comparison=comparison,trimmed_fps=trimmed,
                trimmed_change_pct=100*(trimmed/old['trimmed_fps']-1),phases=phases,
                phase_delta_ms={k:v['ms_per_display']-old['phases'][k]['ms_per_display'] for k,v in phases.items()},
                work_comparison={'662':old_work,'666':current_work},workload_change=workload,
                frame_start_bins=[dict(start_s=i*5,displays=r['frames'],max_gap_ms=r['maxgap']*10) for i,r in enumerate(rows)],
                terminal=dict(commits=commits,retires_EA=ea,pending=pending,serial=serial,generation=generation,
                              request_op=req[0],request_section=req[1],request_offset=offset,request_length=length,
                              last_display_s=int(g['profile_last_display_tick'])/100,run_result=int(g['native_result']),
                              receiver_error=0,video_error=7,sink_error=2,window_error=3,stop_ok=True,base_restored=True,
                              menu_state=g['menu_state'],last_checkpoint=marks[-1][0],stop_to_menu_ms=at['MENU_PREPARED']-at['DISPLAY_STOPPED'],
                              interpretation='DEADLINE is the retained first runtime result. One ordinary map packet is pending without ACK. Planner error 7 includes map-offer callback failure (also other branches); exact failing instruction is not captured. Do not count the pending generation as displayed or interpret this as a proven mid-run tile-capacity fault.'),
                capture_history=history,boot=dict(polls=int(b['boot_polls']),ticks=int(b['boot_ticks'])),
                assessment='Early completion rate slightly higher, late rate and trimmed aggregate lower. Map/OBJ workload is substantially different; neither a matched-work hardware speedup nor an implementation regression is established.',
                limitations=['One unsynchronized playthrough per build.','Work bins use frame start; FPS windows use final completion.',
                             'DWT phases include IRQ and waits; nested SPI/poll counters cannot be added again.',
                             'No physical per-frame DMA/VBlank timings, p95 distribution, or exact terminal PC. Capture episodes have no wall-clock alignment.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('raw','baseline','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();j=analyze(a.raw,a.baseline)
    a.out.write_text(json.dumps(j,indent=2)+'\n',newline='\n')
    print(json.dumps({k:j[k] for k in ('display','completion_comparison','trimmed_change_pct','phases','phase_delta_ms','workload_change','terminal')},indent=2))
