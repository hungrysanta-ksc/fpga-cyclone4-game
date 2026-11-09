"""Separate MMC690 startup failure from completed play; compare with MMC666."""
import argparse,json,re,struct
from pathlib import Path
from analyze_nes_hardware552 import inputs
from analyze_nes_hardware663 import work
from check_nes_fault641 import ROOT,digest,evidence
from decode_nes_minreject180 import decode
from nes_windows518 import windows,duration_ms

def marks(p):
    return {k:int(v) for k,v in re.findall(r'stage=(\w+).*?elapsed_ms=(\d+)',p)}

def analyze(success,failure,baseline):
    old=evidence('hardware667-mmc666.json')
    g,b,p,pins=inputs(success,690)
    _,bb,_,bpins=inputs(baseline,666)
    assert bpins==old['source_SHA256']
    assert all(g[k]=='0' for k in ('run_error','run_rom_error','run_first_error','run_stop_error',
        'fault_context_valid','native_video_error','plan_error','trace_aborts'))
    assert g['run_passed']==g['native_result']=='1' and b['boot_reason']=='1'
    assert b['plan_valid']=='0' and all(b[k]=='0' for k in ('failed_transfers','cost_crc_errors','cost_transfer_stops'))
    assert b['cost_scene_crc32_hex']=='5a04eed7' and b['cost_clock_hz']=='84000000'
    assert b['cost_phase_and_op_are_nested']==b['cost_cycles_include_IRQ_guard_and_wait']=='1'
    n=int(g['native_frames']);elapsed=duration_ms(p)
    split=windows((success/'nes-budget-mmc690.txt').read_text(encoding='utf-8-sig'),elapsed)
    comparison=[dict(**c,previous_displays=o['displays'],previous_fps=o['fps'],
        delta_displays=c['displays']-o['displays'],delta_pct=100*(c['fps']/o['fps']-1))
        for c,o in zip(split,old['completion_windows'],strict=True)]
    phases={}
    for i,k in enumerate(('receive','plan_supply','output_final_ack')):
        calls,_,hi,lo,maximum=map(int,b[f'cost_phase_{i:02}'].split(','))
        phases[k]=dict(calls=calls,ms_per_display=((hi<<32)+lo)/84000/n,max_ms=maximum/84000)
    assert phases['output_final_ack']['calls']==n
    rows,current_work=work(b);_,previous_work=work(bb)
    assert sum(r['frames'] for r in rows)==n
    changes=[dict(start_s=c['start_s'],end_s=c['end_s'],
        per_frame_change_pct={k:100*(v/o['per_frame'][k]-1) for k,v in c['per_frame'].items()},
        output_start_bin_change_pct=100*(c['output_ms']/o['output_ms']-1))
        for c,o in zip(current_work,previous_work,strict=True)]
    commits=int(g['trace_commits']);ea=int(b['cost_op_08'].split(',')[0])
    assert commits==int(g['trace_begins'])==int(g['trace_ends'])==n+1 and ea==n
    pending=(int(g['sink_window_sent'])-int(g['sink_window_retired']))&65535
    assert pending==1 and b['open']=='1'
    assert tuple(g[k] for k in ('native_receiver_error','native_sink_error','sink_window_error',
        'sink_trace_ack_valid','sink_trace_mismatch_hex'))==('21','2','2','0','00')
    req=bytes.fromhex(g['sink_trace_request_hex']);assert req[:2]==bytes((3,0))
    serial,generation=struct.unpack_from('<IH',req,4)
    assert serial==n+1 and generation==int(g['trace_generation'])==int(g['native_generation'])+1
    assert bytes.fromhex(g['sink_trace_ack_hex'])==bytes(12)
    history=decode((success/'nes-game-last-mmc690.txt').read_text(encoding='utf-8-sig'))
    assert [e['event'] for e in history['events']]==['REJECT','RECOVERY','REJECT','RECOVERY','REJECT']
    assert all(e['errors']==0 for e in history['events'])
    fg,fb,fp,fh=inputs(failure,690);fm=marks(fp)
    assert fg['run_passed']=='0' and fg['run_first_error']=='6' and fg['run_stop_error']=='0'
    assert fb['boot_reason']=='5' and fb['boot_ticks']=='500' and fb['cost_sampled']=='0'
    assert all(fg[k]=='0' for k in ('native_frames','native_transactions','trace_begins','trace_commits',
        'screen_stage','plan_error','fault_context_valid'))
    assert fb['display_5_40_55']=='0,0'
    assert all(not any(int(v,16) for v in fb[f'b{i:02}'].split(',')) for i in range(12))
    assert fg['spc_init_status_valid']=='0' and fg['spc_init_status_hex']=='05'
    prior551=evidence('hardware552-mmc551.json')['failure']
    prior639=evidence('hardware640-mmc639.json')['runs'][1]['fields']
    failed=dict(source_SHA256=fh,display_interval_ms=duration_ms(fp),frames=0,native_transactions=0,
        boot_ticks=int(fb['boot_ticks']),polls=int(fb['boot_polls']),first=fb['boot_first_hex'],last=fb['boot_last_hex'],
        signals=fb['boot_signals_hex'],postflight=fb['startup_post_reply_hex'],cost_sampled=False,
        invalid_SPC_value=fg['spc_init_status_hex'],stop_ok=True,base_restored=True,menu_return_observed=True,
        stop_to_menu_ms=fm['MENU_PREPARED']-fm['DISPLAY_STOPPED'],root_cause=None,
        previous=dict(MMC551={k:prior551[k] for k in ('first','last','signals','boot_ticks','polls')},
            MMC639={k:prior639[k] for k in ('boot_first_hex','boot_last_hex','boot_ticks','boot_polls')}),
        assessment='Same five-second pre-native stage0 timeout class as551/639, not proof of the same cause. 0x05 is not a valid SPC result; do not assign an audio failure. Two attempts do not estimate failure probability.')
    at=marks(p);trimmed=sum(w['displays'] for w in split)/50
    return dict(trial=690,trial_family='MMC',physical=True,hardware_run_passed=True,logged_runs=2,completed_runs=1,
        user_report=dict(first_start=False,second_start=True,both_menu_returns=True,perception='almost no FPS difference'),
        source_SHA256=pins,failure=failed,reference='analysis/hardware667-mmc666.json',
        reference_SHA256=digest(ROOT/'analysis/hardware667-mmc666.json'),package='analysis/trial690-package.json',
        package_SHA256=digest(ROOT/'analysis/trial690-package.json'),
        display=dict(completed=n,seconds=elapsed/1000,fps=n*1000/elapsed,mean_ms=elapsed/n),
        completion_windows=split,completion_comparison=comparison,trimmed_fps=trimmed,
        trimmed_change_pct=100*(trimmed/old['trimmed_fps']-1),phases=phases,
        phase_delta_ms={k:v['ms_per_display']-old['phases'][k]['ms_per_display'] for k,v in phases.items()},
        work_comparison={'666':previous_work,'690':current_work},workload_change=changes,
        frame_start_bins=[dict(start_s=i*5,displays=r['frames'],max_gap_ms=r['maxgap']*10) for i,r in enumerate(rows)],
        terminal=dict(commits=commits,retires_EA=ea,pending=pending,serial=serial,generation=generation,
            request_hex=req.hex(),last_display_s=int(g['profile_last_display_tick'])/100,
            receiver_error=21,sink_error=2,window_error=2,video_error=0,run_result=1,stop_ok=True,base_restored=True,
            menu_state=g['menu_state'],last_checkpoint='MENU_PREPARED',stop_to_menu_ms=at['MENU_PREPARED']-at['DISPLAY_STOPPED'],
            interpretation='First runtime result is DEADLINE. Final SEAL is pending. Window2 is guard rejection; receiver21 can be transfer rejection or invalid D0 status. Logs lack exact branch/PC, so do not call it a proven mid-run SPI/CRC fault or count the pending display.'),
        capture_history=history,boot=dict(polls=int(b['boot_polls']),ticks=int(b['boot_ticks'])),
        assessment='Small early gain, essentially unchanged late FPS; workload differs. Output/final ACK still largest measured phase. No matched-work causal FPS proof.',
        limitations=['One successful unsynchronized playthrough per version; failed boot excluded from FPS.',
            'Work bins use frame start, completion windows use final display; DWT phases include IRQ and waits.',
            'No physical per-frame DMA/VBlank split or fault PC; final capture reject has no wall-clock position.'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('success','failure','baseline','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();j=analyze(a.success,a.failure,a.baseline)
    a.out.write_text(json.dumps(j,indent=2)+'\n',newline='\n')
    print(json.dumps({k:j[k] for k in ('display','completion_comparison','trimmed_change_pct','phase_delta_ms','workload_change')},indent=2))
