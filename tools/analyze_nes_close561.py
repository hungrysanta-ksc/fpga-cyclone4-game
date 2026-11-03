# SPDX-License-Identifier: MIT
"""Join the checked 48-byte BG transfer and two continuously replayed display schedules."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_phase537 import Calendar, csv_groups, ms, one, read, sha
from analyze_nes_map553 import map_times
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare
from analyze_nes_supply560 import frame952
from analyze_nes_transfer512 import fpga
from verify_nes_trial533 import timing


def phase(a,i,cal):
    base=a.traces/f'nes-end557-banks-base{i}'
    run=a.traces/f'nes-close561-run{i}'
    ref=read(a.root/'analysis/end557-verification.json')['phases'][i-1]['banks-base']['cost']
    assert ref['pins']['window.csv']==sha(base/'window.csv')
    phases=read(run/'obj-phases.json')
    requests={int(g):v['first_BG561'] for g,v in phases.items() if 'first_BG561' in v}
    cost=inspect_run(run,a.plans,cal,base,sha(a.arm/'obj-nes-100/firmware.stm'),sha(a.client/'sink165.sfc'),
                     first_bg_limit=3,first_bg_requests=requests)
    result={}
    for name,folder,metrics in [('base',base,ref),('early',run,cost)]:
        bus=a.traces/f'nes-close561-bus{name}{i}'
        audit=read(bus/'audit.json')
        assert audit['frames']==53 and audit['trace']==sha(folder/'window.csv')
        cpu=csv_groups(folder/'window.csv')
        previous=one([r for r in cpu[951] if r['op']==3],'reveal')['clock']
        timeline=frame952(folder,a.plans,cal)
        with (bus/'bank561.csv').open() as f:
            rows=[r for r in csv.DictReader(f) if int(r['bytes'])==48]
        assert [r['event'] for r in rows]==['last_read','consume'] and len({r['token'] for r in rows})==1
        marks=timeline['marks']
        marks.update({r['event']+'_ms':ms(int(r['clock'])-previous) for r in rows})
        assert marks['BG48_packet_push_ms']<marks['last_read_ms']<marks['consume_ms']<marks['BG48_packet_ACK_ms']
        tail=[r for r in cpu[957] if r['op']==3]
        waits957=sum(r['event']=='wait169' and r['clock']>=one(tail,'final212')['clock'] for r in tail)
        early957=sum(r['push_minus_last_tile_ACK_ms']<0 for r in map_times(folder)['maps'])
        result[name]=dict(timeline=timeline,waits=metrics['waits'],waits957=waits957,early957=early957,
                          audit=audit,bank_trace=sha(bus/'bank561.csv'),**{k:metrics[k] for k in
                          ('dense_VB','dense_ms','last_ACK','dense_frames','SPI_B','ROM_reads','DMA_B','ARM_instructions','IRQ','pins')})
    for key in ('ROM_reads','DMA_B'):
        assert result['base'][key]==result['early'][key]
    result['delta']=compare(cost,ref)
    result['later_BG']=[g for g,r in cost['BG'].items() if r['relative_window']>ref['BG'][str(g)]['relative_window']]
    dense=cost['dense_frames']
    vb=lambda g:dense[g]['before_head']+dense[g]['after_head']
    result['timing_gate']=(vb(952)<=5 and vb(953)<=5 and vb(954)<=5 and not result['later_BG'] and
        not any(cost['waits'].values()) and not waits957 and early957>=2 and all(v<0 for v in result['delta'].values()))
    return result


def main(a):
    cal=Calendar(a.calendar)
    results=[phase(a,i,cal) for i in (1,2)]
    rtl=read(a.rtl/'result.json')
    assert len(rtl)==10
    boards={}
    for name,d in [('base',a.base),('candidate',a.board)]:
        raw,worst,unconstrained=timing(d)
        boards[name]=dict(cost=fpga(d),raw_worst=worst,unconstrained=unconstrained,sta_rows=raw,sof=sha(d/'output_files/board.sof'))
        with (d/'close561-crossings.tsv').open() as f:
            crossings=list(csv.DictReader(f,delimiter='\t'))
        assert len(crossings)==6
        boards[name]['setup_recovery_endpoints']=crossings
    with (a.board/'close561-paths.tsv').open() as f:
        paths=list(csv.DictReader(f,delimiter='\t'))
    assert {r['boundary'] for r in paths}=={'marker_in','marker_out','decoder','tile','host'}
    specific={group:{c:min(float(r['slack']) for r in paths if r['boundary']==group and r['check']==c)
                     for c in ('setup','hold')} for group in sorted({r['boundary'] for r in paths})}
    base_rows=boards['base']['sta_rows'];early_rows=boards['candidate']['sta_rows']
    assert early_rows.keys()==base_rows.keys()
    regressions={k:[base_rows[k],v] for k,v in early_rows.items() if v[0]<min(0,base_rows[k][0])}
    pins=read(a.root/'analysis/trial558-verification.json')['inputs']
    changed=sorted(n for n,h in pins.items() if sha(a.board/n)!=h)
    assert changed==['nes_direct206.sv','nes_tile_bulk206.sv'] and all(sha(a.base/n)==h for n,h in pins.items())
    return dict(phases=results,rtl=rtl,boards=boards,changed=changed,local_paths=specific,
                regressed_negative_STA_rows=regressions,trial_gate=all(r['timing_gate'] for r in results) and not regressions,
                firmware=sha(a.arm/'obj-nes-100/firmware.stm'),client=sha(a.client/'sink165.sfc'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','client','plans','calendar','traces','rtl','base','board','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.root=Path(__file__).resolve().parents[1]
    a.out.write_text(json.dumps(main(a),indent=2)+'\n')
