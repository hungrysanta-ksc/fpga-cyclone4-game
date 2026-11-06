# SPDX-License-Identifier: MIT
"""Match the 950 fence and the 951 receiver/beam results to the input schedule."""
import argparse
import csv
import json
import math
from pathlib import Path
from analyze_nes_map628 import csv_groups, ms, one, read, sha
from replay_nes_overlap634 import ledger


def summarize(root, arm):
    phases=[]
    for phase in (1,2):
        trace=root/f'nes-seal625-tables-bg-{phase}'
        original=csv_groups(trace/'window.csv')
        ref=read(root/f'nes-bank633-control-{phase}a/audit.json')
        events=read(trace/'events.json')
        src=[e for e in events if e['generation']==951]
        params=read(trace/'joint.json')['parameters']
        period=341*262*4
        def next_capture(d2):
            p=params['ROM_phase']
            return p+(math.floor((d2-p)/period)+1)*period
        last_pop=[e for e in src if e.get('opcode')=='0xd2'][-1]['clock']
        budgets={};runs={}
        for policy in ('fixed','buffer','restore'):
            plan=ledger(trace,policy)
            ea=plan['ea']
            assert next_capture(last_pop)+240*341*4==plan['capture952_ready_recorded']
            shifted=next_capture(last_pop-plan['shift'])
            budgets[policy]=dict(blocks=len(plan['scheduled']),source_B=plan['bytes'],shift_ms=ms(plan['shift']),
                original_polls_skipped=plan['omitted_original_polls'],longest_poll_ms=plan['max_poll_interval_ms'],
                first_D1_ms=plan['first_D1_ms'],max_fixed_gap_ms=plan['max_fixed_gap_ms'],
                scheduled=[(ms(r['start']-ea),ms(r['end']-ea)) for r in plan['scheduled']],
                capture_ready_ms=ms(plan['capture_ready']-ea),old_last_DMA_ms=ms(plan['last_dma']-ea),
                old_display_ms=ms(plan['show']-ea),old_ACK_ms=ms(plan['ack']-ea),
                planner_projected_ms=ms(plan['planner']-plan['shift']-ea),
                map_frozen_projected_ms=ms(plan['bg_frozen']-plan['shift']-ea),
                E9_projected_ms=ms(plan['first_plan']-plan['shift']-ea),
                next_capture_start_projected_ms=ms(shifted-ea),
                last_OBJ_projected_ms=ms(plan['last_obj']-plan['shift']-ea))
            for mode in (('control',) if policy=='fixed' else ('control','collapse')):
                d=root/f'nes-overlap634-{policy}-{mode}-{phase}c'
                a=read(d/'audit.json')
                w=csv_groups(d/'window.csv')
                assert a['feedback'] and a['overlap']['scheduled']==plan['scheduled']
                assert all(w[g]==original[g] for g in range(905,951))
                if policy=='fixed':
                    assert w[951]==original[951]
                q=list(csv.DictReader((d/'queue.csv').read_text().splitlines()))
                assert len(q)==(30 if mode=='control' else 24) and max(int(e['depth']) for e in q)<=4
                seal=[r for r in w[951] if r['op']==3]
                check=one(seal,'final_upload212_same_blank212')
                assert check['line']<=246 and check['frame']==a['show']['frame']
                base=read(root/f'nes-bank633-{mode}-{phase}a/audit.json')
                runs[f'{policy}_{mode}']=dict(interval=a['interval'],ACK=a['ack'],
                    delta_625_ms=ms(a['ack']-ref['ack']),delta_matched_ms=ms(a['ack']-base['ack']),
                    first_map_load_ms=ms(next(r['clock'] for r in w[951] if r['section']==2 and r['event']=='load')-ea),
                    SEAL_vs_cutoff_ms=ms(a['seal']-a['cutoff']),decision_line=check['line'],
                    reveal_line=a['show']['line'],reveal_vs_cutoff_ms=ms(a['show']['clock']-a['cutoff']),
                    actual_trace=a['trace'],offers=a['offers'],queue=sha(d/'queue.csv'))
        phases.append(dict(phase=phase,budgets=budgets,runs=runs,
                           trace_hashes={s:sha(trace/s) for s in ('events.json','obj-phases.json','window.csv')}))
    return dict(phases=phases,ARM=read(arm))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('root','arm','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(summarize(a.root,a.arm),indent=2)+'\n',newline='\n')
