# SPDX-License-Identifier: MIT
"""Pair the MMC551 boot timeout with a completed playthrough without pooling them."""
import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
from analyze_nes_hardware521 import ROOT, fields, sha, windows, duration_ms
from analyze_nes_phase537 import csv_groups, one, ms


def inputs(folder):
    paths={k:folder/f'nes-{k}-mmc551.txt' for k in ('game-last','budget','progress')}
    g,b=(fields(paths[k].read_text(encoding='utf-8-sig')) for k in ('game-last','budget'))
    p=paths['progress'].read_text(encoding='utf-8-sig')
    assert all(l.startswith('MMC551 seq=') for l in p.splitlines() if l.strip())
    assert all(g[k]=='1' for k in ('verified','end_accepted','start_sent','stop_ok','base_restored','safe_to_reload'))
    assert g['candidate']=='NES-MMC551' and g['menu_state']=='PREPARED_RESET_HELD'
    assert g['loaded_bytes']==g['compared_bytes']=='393216' and g['run_rom_error']==g['verify_error']=='0'
    return g,b,p,{p.name:sha(p) for p in paths.values()}


def performance(raw,old):
    g,b,p,pins=inputs(raw)
    elapsed=duration_ms(p)
    n=int(g['native_frames'])
    assert g['run_passed']==g['native_result']=='1' and b['boot_reason']=='1'
    assert int(g['trace_commits'])==int(g['trace_ends'])==int(b['cost_op_08'].split(',')[0])==n
    assert int(g['trace_begins'])==n+1 and g['trace_aborts']=='0'
    assert g['sink_window_sent']==g['sink_window_retired'] and g['native_receiver_error']=='24'
    assert g['native_sink_error']==g['native_video_error']==g['plan_error']==g['sink_window_error']=='0'
    assert b['cost_scene_crc32_hex']=='5a04eed7' and b['cost_counter_available']=='1'
    assert b['cost_crc_errors']==b['cost_transfer_stops']==b['failed_transfers']=='0'
    split=windows((raw/'nes-budget-mmc551.txt').read_text(encoding='utf-8-sig'),elapsed)
    cols=b['columns'].split(',')
    rows=[dict(zip(cols,[int(x,16) for x in b[f'b{i:02}'].split(',')],strict=True)) for i in range(12)]
    assert sum(x['frames'] for x in rows)==n
    bins=[dict(start_s=5*i,displays=r['frames'],max_gap_ms=r['maxgap']*10) for i,r in enumerate(rows)]
    matched=[]
    for lo,hi in ((5,40),(40,55),(5,55)):
        counts=[sum(r['displays'] for r in src if lo<=r['start_s']<hi) for src in (old['frame_start_bins'],bins)]
        matched.append(dict(start_s=lo,end_s=hi,old=counts[0],new=counts[1],change_pct=100*(counts[1]/counts[0]-1)))
    phases={}
    for i,k in enumerate(('receive','plan_supply','output_final_ack')):
        calls,_,hi,lo,_=map(int,b[f'cost_phase_{i:02}'].split(','))
        phases[k]=dict(calls=calls,ms_per_display=((hi<<32)+lo)*1000/int(b['cost_clock_hz'])/n)
    return dict(display=dict(completed=n,seconds=elapsed/1000,fps=n*1000/elapsed,mean_ms=elapsed/n),
                completion_windows=split,trimmed_fps=sum(w['displays'] for w in split)/50,
                frame_start_bins=bins,matched_start_bins=matched,phases=phases,source_SHA256=pins,
                queue_sent_retired=int(g['sink_window_retired']),boot_polls=int(b['boot_polls']),boot_ticks=int(b['boot_ticks']))


def failure(raw):
    g,b,p,pins=inputs(raw)
    assert g['run_passed']=='0' and g['run_first_error']=='6' and g['run_stop_error']=='0'
    assert b['boot_reason']=='5' and b['startup_post_reason']=='1' and b['boot_ticks']=='500'
    assert g['native_frames']==g['native_transactions']==g['trace_begins']==g['screen_stage']=='0'
    assert b['display_5_40_55']=='0,0' and all(not any(int(x,16) for x in b[f'b{i:02}'].split(',')) for i in range(12))
    return dict(source_SHA256=pins,display_interval_ms=duration_ms(p),frames=0,native_transactions=0,
                postflight=b['startup_post_reply_hex'],boot_reason='TIMEOUT',polls=int(b['boot_polls']),
                boot_ticks=int(b['boot_ticks']),first=b['boot_first_hex'],last=b['boot_last_hex'],
                signals=b['boot_signals_hex'],stale_output_phase_calls=int(b['cost_phase_02'].split(',')[0]),
                root_cause=None,menu_return_observed=True)


def tail(folder,g):
    events=json.loads((folder/'events.json').read_text())
    start=one([r for r in events if r['generation']==g],'output_enter531')['clock']
    groups=csv_groups(folder/'window.csv')
    cpu=groups[g]
    seal=[r for r in cpu if r['op']==3]
    head=one(seal,'load')['clock']
    last=max(r['clock'] for r in cpu if r['event']=='ack' and r['op']==7)
    packets=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    rest=[bytes.fromhex(h) for _,t,h,_ in packets if last<t<=head]
    assert rest[-1][0]==3
    pushes=[r[1] for r in packets]
    retired=sorted(r['clock'] for group in groups.values() for r in group if r['event']=='ack')
    depth=bisect_right(pushes,last)-bisect_right(retired,last)
    edges=Counter(t for t in pushes if last<t<head)
    edges.subtract(t for t in retired if last<t<head)
    occupancy=Counter()
    previous=last
    for t,change in sorted(edges.items()):
        assert 0<=depth<=4
        occupancy[depth]+=ms(t-previous)
        depth+=change
        previous=t
    occupancy[depth]+=ms(head-previous)
    assert abs(sum(occupancy.values())-ms(head-last))<1e-6
    return dict(output_to_head_ms=ms(head-start),head_to_display_ACK_ms=ms(one(seal,'ack')['clock']-head),
                last_bulk_ACK_to_head_ms=ms(head-last),post_bulk_E1=len(rest),post_bulk_E1_wire_B=sum(len(h)+3 for h in rest),
                post_bulk_packet_kinds=[[h[0],h[1]] for h in rest],post_bulk_depth_ms=occupancy)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('success','failure','traces','guards','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    old=json.loads((ROOT/'analysis/hardware541-mmc540.json').read_text())
    result=dict(trial=551,trial_family='MMC',physical=True,hardware_run_passed=True,
                user_observation='Similar first-level play on successful launch. Both attempts returned to menu. Frequency unknown.',
                failure=failure(a.failure),report_fix=json.loads(a.guards.read_text()),**performance(a.success,old))
    result['coupled_output_tail']=[]
    ref=json.loads((ROOT/'analysis/upload550-verification.json').read_text())
    for i in (1,2):
        f=a.traces/f'nes-upload550-joint{i}'
        assert all(sha(f/n)==h for n,h in ref['phases'][i-1]['measured']['pins'].items())
        result['coupled_output_tail'].append({g:tail(f,g) for g in (951,953,957)})
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
