# SPDX-License-Identifier: MIT
"""Cost of an idle-built row proof on the 753 release calendar."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_owner739 import ms, read, sha


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def cpu_clock(records, g, op, event, section=None):
    value, = [int(r['clock']) for r in records if int(r['g'])==g and int(r['op'])==op
              and r['event']==event and (section is None or int(r['section'])==section)]
    return value


def measure(temp, phase):
    run = temp/f'nes-idle761-row{phase}'
    root = temp/f'nes-credit753-prefix{phase}'
    baseline = rows(root/'window.csv')
    cpu = rows(run/'window.csv')
    probe = rows(run/'idle761.csv')
    cost = read(run/'cost761.json')
    def marks(name):
        return [int(r['clock']) for r in probe if r['event']==name]
    begins, ends = marks('read_chunk761'), marks('idle_yield761')
    assert len(begins)==len(ends)==48 and all(a<b for a,b in zip(begins,ends))
    assert all(b<a for b,a in zip(ends[:-1],begins[1:]))
    assert cost['commits']==53 and cost['checked_rows']==24 and cost['changes']==34
    ack955 = cpu_clock(cpu,955,3,'ack')
    original_ack = cpu_clock(baseline,955,3,'ack')
    load = cpu_clock(cpu,957,9,'load',2)
    verify, finish, reply = (cost[k+'_clock'] for k in ('verify','finish','reply'))
    assert ack955 < begins[0] < cost['ready_clock'] < load < verify < finish < reply
    actual=read(run/'result.json')
    assert actual['passed'] and read(run/'audit.json')['prefix_through']==954
    return dict(**cost, idle_worker_ms=ms(sum(b-a for a,b in zip(begins,ends))),
                longest_quantum_ms=ms(max(b-a for a,b in zip(begins,ends))),
                ack955_delta_ms=ms(ack955-original_ack), ack955_to_ready_ms=ms(cost['ready_clock']-ack955),
                ready_before_head_ms=ms(load-cost['ready_clock']), header_restore_ms=ms(verify-load),
                live_readback_ms=ms(finish-verify), coverage_reply_ms=ms(reply-finish),
                tail_ms=ms(reply-verify), pins={p:sha(run/p) for p in
                    ('handler.bin','capture.lua','arrivals.tsv','idle761.csv','window.csv','result.json')})


def analyze(temp):
    phases={i:measure(temp,i) for i in (1,2)}
    floor=temp/'nes-idle761-row-floor2'
    skipped=read(floor/'cost761.json')
    assert skipped['commits']==53 and skipped['verify_clock']==phases[2]['verify_clock']
    floor_ms=ms(skipped['verify_and_ACK_clocks'])
    faults={}
    for f in ('retained','mirror','partial'):
        folder=temp/f'nes-idle761-row-{f}2'
        data=read(folder/'cost761.json')
        assert data['commits']==52 and data['status']==(0xe4 if f=='partial' else 0xe0)
        assert data['RGB956']==sha(temp/'nes-credit753-prefix2/frame-956.rgb')
        faults[f]=dict(**data, trace=sha(folder/'idle761.csv'))
    old=read(Path(__file__).resolve().parents[1]/'analysis/page760-verification.json')['phases']['2']['variants']['indexed']
    room = old['fixed_order_max_service_ms'] - old['ms']['entry'] - old['ms']['restore']
    return dict(selected='753',scope='65816 replay with recorded 753 arrivals, one page in bank 0; no new ARM or FPGA',
                phases=phases,threshold_ms=room,phase2_excess_ms=phases[2]['tail_ms']-room,
                unchecked_floor_ms=floor_ms,margin_after_unchecked_floor_ms=room-floor_ms,
                unchecked_pins={p:sha(floor/p) for p in ('handler.bin','result.json','idle761.csv')},
                faults=faults,passed_threshold=phases[2]['tail_ms']<=room)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temp',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args.temp),indent=2)+'\n',encoding='utf8',newline='\n')
