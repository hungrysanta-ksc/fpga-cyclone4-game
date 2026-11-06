# SPDX-License-Identifier: MIT
"""Check real queue gaps, DMA end clocks, and displayed generation in both replays."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map628 import csv_groups, ms, read, sha


def summarize(root):
    results=[]
    for phase in (1,2):
        ref=read(root/f'nes-bank633-control-{phase}a/audit.json')
        runs={}
        for mode in ('control','gap','collapse','wire'):
            d=root/f'nes-bank633-{mode}-{phase}a'
            a=read(d/'audit.json')
            assert a['previous']==ref['previous'] and a['cutoff']==ref['cutoff'] and a['client']==ref['client']
            q=list(csv.DictReader((d/'queue.csv').read_text().splitlines()))
            r=csv_groups(d/'window.csv')[951]
            retire={e['index']:e['clock'] for e in r if e['event']=='ack'}
            assert len(q)==len(retire)==(30 if mode=='control' else 24)
            assert all(int(e['offer'])<=int(e['admit'])<=retire[int(e['index'])] and 1<=int(e['depth'])<=4 for e in q)
            cutoff=a['cutoff']
            transfers=[]
            for m in a['maps']:
                if m['frame']!=a['goal']:
                    continue
                issued=sum(int(e['offer'])<=m['start'] for e in q)
                acked=sum(t<=m['start'] for t in retire.values())
                # Even counting every offered head immediately (before the
                # emulator samples the queue), all of them had been retired.
                assert issued==acked
                previous=max(t for t in retire.values() if t<=m['start'])
                following=min(int(e['offer']) for e in q if int(e['offer'])>m['start'])
                transfers.append(dict(**m, empty_before_ms=ms(m['start']-previous),
                                      next_offer_after_start_ms=ms(following-m['start']),
                                      start_ms=ms(m['start']-cutoff),end_ms=ms(m['end']-cutoff)))
            seal=[e for e in r if e['op']==3]
            seal_dma=[e for e in seal if e['event']=='ppu_dma' and e['frame']==a['goal']]
            goal_early=[e for e in transfers if e['end']<=cutoff]
            runs[mode]=dict(interval=a['interval'],goal_frame=a['goal'], displayed_frame=a['show']['frame'],
                            displayed_line=a['show']['line'], final_ack=a['ack'],
                            ack_delta_ms=ms(a['ack']-ref['ack']),head_advance_ms=ms(ref['seal']-a['seal']),
                            schedule_credit_ms=a['schedule_credit_ms'], computed_offer_ms=ms(int(q[-1]['offer'])-cutoff),
                            seal_head_ms=ms(a['seal']-cutoff),upload_ms=ms(a['upload']-cutoff),
                            reveal_ms=ms(a['show']['clock']-cutoff), idle_map=transfers,
                            map_B_in_complete_DMA_by_cutoff=sum(m['size'] for m in goal_early),
                            seal_dma=[dict(size=e['value'],line=e['line'],start_ms=ms(e['clock']-cutoff)) for e in seal_dma],
                            trace=a['trace'],offers=a['offers'],queue=sha(d/'queue.csv'))
        results.append(dict(phase=phase,client=ref['client'],cutoff=ref['cutoff'],runs=runs))
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(summarize(a.root),indent=2)+'\n',newline='\n')
