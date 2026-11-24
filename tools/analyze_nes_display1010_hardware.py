"""Compare the two MMC1010 hardware runs with the pinned MMC966 display counts and workloads."""
import argparse
import hashlib
import json
import re
import statistics
import struct
from collections import Counter
from pathlib import Path

from analyze_nes_obj967 import matched_workloads
from read_nes_display1010 import ARM_TICK, HEADER, MS, ROW, decode
from read_nes_frame900 import PERIOD

ROOT = Path(__file__).resolve().parents[1]


def fields(path):
    return dict(line.split('=',1) for line in path.read_text(encoding='utf-8-sig').splitlines() if '=' in line)


def run(directory, trial, reference):
    paths = {key:directory/f'nes-{key}-mmc1010-{trial}차.{ext}' for key,ext in (
        ('budget','txt'),('game-last','txt'),('progress','txt'),('frame','bin'))}
    budget = fields(paths['budget'])
    game = fields(paths['game-last'])
    stages = re.findall(r'MMC1010 seq=\d+ stage=(\w+)',paths['progress'].read_text())
    assert stages[-1]=='MENU_PREPARED' and stages.index('STOP_DONE')<stages.index('BASE_DONE')
    assert game['candidate']=='NES-MMC1010' and all(game[k]=='1' for k in
        ('verified','stop_ok','base_restored','safe_to_reload','run_passed'))
    assert game['loaded_bytes']==game['compared_bytes']=='393216'
    assert game['run_error']==game['trace_aborts']==budget['failed_transfers']=='0'
    assert budget['tick_ms']=='10' and budget['bin_basis']=='FRAME_START_NOT_SCENE'
    trace = decode(paths['frame'])
    data = paths['frame'].read_bytes()
    rows = trace['rows']
    assert not any(trace['dropped']) and len(rows)==int(budget['b11'].split(',')[0],16)
    assert HEADER.unpack_from(data)[2] in (0,2)
    for i,r in enumerate(rows):
        assert 'invalid' not in r and 5500<=r['tick']<6000
        *_,h,desc = ROW.unpack_from(data,HEADER.size+i*ROW.size)
        ready,kind,size,offset,g,token=struct.unpack('<BBHHHI',desc)
        assert ready==1 and kind<=1 and g==r['generation'] and 0<size<=2048 and size%(16<<kind)==0
        assert token==int.from_bytes(h[12:16],'little')
        if i: assert rows[i-1]['show']==r['previous_show']
        vb=round(r['spacing_ms']/PERIOD)
        assert abs(r['spacing_ms']-vb*PERIOD)+MS<PERIOD/2
        r.update(last_kind=kind,last_bytes=size,last_offset=offset,vblanks=vb,
                 tile_to_seal_ms=r['last_tile_to_show_ms']-r['seal_to_show_ms'],
                 seal_to_last_dma_ms=r['seal_to_show_ms']-r['dma_to_show_ms'])
    refs=reference['runs']['966']['rows']
    pairs=matched_workloads(refs,rows)
    wanted=reference['both_long_after_tile_with_supply_under_2ms']+[1452]
    matched={a['generation']:b for a,b in pairs if a['generation'] in wanted}
    spike=max(rows,key=lambda r:r['spacing_ms'])
    previous=rows[rows.index(spike)-1]
    # FPGA uses a different clock from ARM. Bound previous show to input COMPLETE
    # with one timestamp difference error on the FPGA plus ARM age truncations.
    before=(spike['final_ACK']-spike['previous_show'])*MS-spike['input_to_E0_ms']
    lo,hi=spike['final_ACK_to_ARM_E0_ms']
    counts=list(map(int,budget['display_1_30_60'].split(',')))
    return dict(files={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},
        frame_counts=counts,fps=[v/t for v,t in zip(counts,(29,30))],displayed55=trace['displayed55'],
        recorded=len(rows),dropped=trace['dropped'],vblanks=Counter(r['vblanks'] for r in rows),
        matches=len(pairs),targets=matched,
        post_tile_over_period=sum(r['last_tile_to_show_ms']-MS>PERIOD for r in rows),
        fast_supply_slow_show=sum(r['supply_ms']+MS<2 and r['last_tile_to_show_ms']-MS>PERIOD for r in rows),
        median_supply_ms_by_spacing={vb:statistics.median(r['supply_ms'] for r in rows if r['vblanks']==vb)
                                    for vb in sorted(set(r['vblanks'] for r in rows))},
        E0_upper_median_ms=statistics.median(r['final_ACK_to_ARM_E0_ms'][1] for r in rows),
        spike=dict(row=spike,previous_generation=previous['generation'],
            previous_show_to_E9_ms=spike['spacing_ms']-spike['supply_ms']-spike['last_tile_to_show_ms'],
            previous_show_to_input_complete_bounds_ms=[before+lo-MS-2*ARM_TICK,before+hi+MS+2*ARM_TICK]),
        transport_snapshot={k:game[k] for k in ('native_result','trace_commits','trace_aborts',
            'sink_window_sent','sink_window_retired','sink_window_error','native_sink_error','plan_error')})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args()
    ref=json.loads((ROOT/'analysis/demo-loss1009-results.json').read_bytes())
    result=dict(reference_display_counts=ref['runs']['966']['displayed_1_30_and_30_60'],
                fpga_tick_ms=MS,runs=[run(args.directory,n,ref) for n in (1,2)])
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
