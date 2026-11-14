# SPDX-License-Identifier: MIT
"""Isolate 969 ordinary admission in the original empty map-wait interval."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from analyze_nes_output768 import csv_groups, one, read
from trace_nes_owner739 import observe


def run(a):
    a.frames=66
    ev=[r for r in read(a.trace/'events.json') if r['generation']==969]
    times=[r for r in ev if r.get('opcode')=='0xe1']
    w=csv_groups(a.trace/'window.csv')[969]
    lastmap=max(r['clock'] for r in w if r['section']==2 and r['event']=='ack')
    # Wait for the original, validated empty status after that actual return.
    status=next(r for r in ev if r.get('opcode')=='0xe0' and r['start']>lastmap and bytes.fromhex(r['reply'])[2]==2)
    cursor=status['clock']
    start=cursor
    charge={op:next(r['clock']-r['start'] for r in ev if r.get('opcode')==op) for op in ('0xe0','0xe8')}
    def edit(s):
        nonlocal cursor
        for src in a.trace.glob('colors636-*.bin'):
            (a.out/src.name).write_bytes(src.read_bytes())
        path=a.out/'arrivals.tsv'
        rows=[line.split('\t') for line in path.read_text().splitlines()]
        group=[i for i,(_,h,_) in enumerate(rows[:-1]) if bytes.fromhex(h[16:20])==(969).to_bytes(2,'little')]
        assert len(group)==len(times)
        moved=[]
        for i,tx in zip(group,times):
            t,h,_=rows[i]
            h=bytes.fromhex(h)
            if h[0]!=9 and not (h[1]==5 and int.from_bytes(h[10:12],'little') in (0,21)):continue
            assert cursor<tx['start']
            cursor+=charge['0xe0']+charge['0xe8']+tx['clock']-tx['start']
            rows[i][0]=str(round(cursor))
            moved.append(tx['bytes'])
        assert moved==[135,40,21]
        # Counterfactual ARM dispatch: replace no-payload E0/D0 polling here.
        # The linked run separately charges real ARM work, input service and IRQ.
        assert all(r.get('opcode') in ('0xe0','0xd0') for r in ev if r['event']=='SPI' and start<=r['start']<cursor)
        ordered=sorted((rows[i] for i in group),key=lambda row:int(row[0]))
        for seq,(i,(clock,h,tile)) in enumerate(zip(group,ordered)):
            rows[i]=[clock,h[:4]+seq.to_bytes(2,'little').hex()+h[8:],tile]
        path.write_text(''.join('\t'.join(r)+'\n' for r in rows),newline='\n')
        return s
    def compare(old,new):
        assert [r for r in old if int(r['g'])<969]==[r for r in new if int(r['g'])<969]
        cpu=csv_groups(a.out/'window.csv')
        q=cpu[969]
        start=one(ev,'output_enter531')['clock']
        seal=one([r for r in q if r['op']==3],'load')
        show=lambda g:one([r for r in cpu[g] if r['op']==3],'reveal')
        dma=[[r['value'],r['line']] for r in q if r['event']=='ppu_dma' and start<r['clock']<seal['clock']]
        fields={key:one([r for r in q if r['op']==op and r['section']==sec],mark)['clock']
                for key,op,sec,mark in [('OAM',9,4,'ack'),('padding',5,5,'ack')]}
        return dict(pre_DMA=dma,ready_status=status['clock'],last_early_push=cursor,early_receipts=fields,
                    interval969=show(969)['frame']-show(968)['frame'],SEAL=seal['clock'],
                    ACK969=one([r for r in q if r['op']==3],'ack')['clock'],
                    ACK970=one([r for r in cpu[970] if r['op']==3],'ack')['clock'])
    with patch.object(replay,'observe',observe):
        replay.run(a,edit_script=edit,compare_trace=compare)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','out','mesen','client'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
