# SPDX-License-Identifier: MIT
"""Separate packet receipt, blank occupancy and the final beam sample on 545 and 546."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean

from analyze_nes_drain543 import delta
from analyze_nes_frontier536 import ledger
from analyze_nes_phase537 import Calendar, csv_groups, ms, one, read, sha
from analyze_nes_seal538 import inspect_run

ROOT = Path(__file__).resolve().parents[1]


def timing(folder):
    rows = csv_groups(folder/'window.csv')[957]
    seal = [r for r in rows if r['op']==3]
    entry = one(seal,'final212')
    samples = csv_groups(folder/'seal528.csv')[957]
    latch, = [r for r in samples if r['event']=='latch' and r['clock']>=entry['clock']]
    waits = sum(r['event']=='wait169' and r['clock']>=entry['clock'] for r in seal)
    late = max(0,(latch['line']-247)*1364+latch['h']+1)
    assert bool(late)==bool(waits)
    return dict(final_entry=entry['line'],latch_line=latch['line'],latch_h=latch['h'],
                clocks_to_recover=late,waits=waits,SEAL_head_line=one(seal,'load')['line'])


def repeat_rows(folder):
    # Offline feasibility only. The production client does not retain this oracle.
    records=[bytes.fromhex(json.loads(s)[2]) for s in (folder/'packets.jsonl').read_text().splitlines()]
    out={}
    for g in (951,952,953,954,955,957):
        arrays=[]
        for gen in (g-2,g):
            seal,=[b for b in records if b[0]==3 and int.from_bytes(b[8:10],'little')==gen]
            count=int.from_bytes(seal[38:40],'little')
            assert count==2
            data=(folder/f'expected-{gen}.bin').read_bytes()
            arrays.append([bytes(data[1121+t*64+plane*16+row*2+k] for t in range(32) for k in range(2))
                           for plane in range(3) for row in range(count)])
        out[g]=[i for i,(old,new) in enumerate(zip(*arrays)) if old==new]
    return out


def analyze(args):
    base_proof=read(ROOT/'analysis/repeat545-verification.json')
    original=read(ROOT/'analysis/first539-verification.json')
    fw=base_proof['control_firmware']
    client=sha(args.client/'sink165.sfc')
    phases=[]
    for i in (1,2):
        base=args.traces/f'nes-repeat545-run{i}'
        run=args.traces/f'nes-header546-run{i}'
        audit=args.traces/f'nes-header546-audit{i}'
        fixed=args.traces/f'nes-header546-fixed{i}'
        before=base_proof['phases'][i-1]['candidate']
        assert all(sha(base/f)==digest for f,digest in before['pins'].items())
        row=inspect_run(run,args.plans,Calendar(args.calendar),base,fw,client)
        replay=read(audit/'audit.json')
        assert replay['frames']==53 and replay['trace']==row['pins']['window.csv']
        assert sha(run/'tile532.csv')==sha(audit/'tile532.csv')
        with (audit/'headers546.csv').open() as f:
            headers=list(csv.DictReader(f))
        assert len(headers)==row['packets']
        assert all(int(h['index'])==idx and int(h['reads'])==16 for idx,h in enumerate(headers,1))
        before_marks=csv_groups(args.traces/f'nes-repeat545-audit{i}'/'decode544.csv')
        after_marks=csv_groups(audit/'decode544.csv')
        def dispatch(marks,folder):
            wire=[bytes.fromhex(json.loads(s)[2]) for s in (folder/'packets.jsonl').read_text().splitlines()]
            by_index={}
            for r in marks[957]:
                packet=wire[r['index']-1]
                if packet[1]==5 and int.from_bytes(packet[8:10],'little')==957:
                    key=(packet[0],int.from_bytes(packet[10:12],'little'))
                    by_index.setdefault(key,{})[r['event']]=r['clock']
            return {k:ms(v['packed_header181']-v['header']) for k,v in by_index.items()}
        old_dispatch,new_dispatch=dispatch(before_marks,base),dispatch(after_marks,run)
        assert old_dispatch.keys()==new_dispatch.keys()
        windows=ledger(run,audit,targets=((957,2048),))[957]['windows']
        last=max(windows,key=lambda w:w['open_ms'])
        same=delta(row,before)
        versus_original=delta(row,original['phases'][i-1]['row'])
        gate=all(d['last_ACK_ms']<0 and d['dense_VB']<0 and d['dense_ms']<0 and not d['later_BG_windows']
                 for d in (same,versus_original)) and not any(row['waits'].values()) and timing(run)['waits']==0
        pins=read(fixed/'pins.json')
        assert pins['candidate_client']==client and pins['packets']==before['pins']['packets.jsonl']
        fixed_proof=read(fixed/'run/audit.json')
        assert fixed_proof['frames']==53
        phases.append(dict(phase=i,candidate=row,versus_545=same,versus_MMC540=versus_original,
                           baseline_957=timing(base),fixed_957=timing(fixed/'run'),candidate_957=timing(run),
                           fixed_last_ACK_delta_ms=ms(fixed_proof['last_ACK_delta_clocks']),
                           last_blank_957=dict(queue=last['queue_at_open'],head_ms=sum(r['ms'] for r in last['head_service']),
                                               early_map_B=sum(r['B'] for r in last['grants'] if r['offset'] is not None)),
                           mean_header_through_dispatch_957_ms=[mean(v.values()) for v in (old_dispatch,new_dispatch)],
                           checked_headers=len(headers),header_trace=sha(audit/'headers546.csv'),replay=replay,gate=gate))
    guards={n:read(args.traces/f'nes-header546-{n}'/'result.json') for n in ('stops','final','priority')}
    assert all(r['status']==0xe4 and r['commits']==r['generation']-905 for n in ('stops','final') for r in guards[n])
    assert [len(guards[n]) for n in ('stops','final','priority')]==[8,7,22]
    return dict(phases=phases,gate=all(p['gate'] for p in phases),guards=guards,body_B=len((args.client/'body.bin').read_bytes()),
                client_SHA256=client,base_client_SHA256=base_proof['program_SHA256'],firmware_SHA256=fw,
                exact_raw_row_matches_vs_previous_same_bank=repeat_rows(args.traces/'nes-repeat545-run1'),
                scope='Two 53-frame fixed-capture closed-loop simulations; [5,40)/[40,55) counter firmware. No physical run.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','client','plans','calendar','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=analyze(args)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'gate':result['gate'],'deltas':[p['versus_545'] for p in result['phases']]}))
