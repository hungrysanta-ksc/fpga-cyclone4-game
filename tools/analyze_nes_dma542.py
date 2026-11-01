# SPDX-License-Identifier: MIT
"""Partition actual SEAL elapsed clocks without adding nested ARM/SPI counters."""
import argparse
import json
from collections import Counter
from pathlib import Path
from analyze_nes_phase537 import Calendar, csv_groups, one, read, sha, ms
from analyze_nes_seal538 import inspect_run


def partition(folder):
    cpu=csv_groups(folder/'window.csv')
    events=read(folder/'events.json')
    dma=csv_groups(folder/'seal528.csv')
    result={}
    # Cold forced-blank capture lacks the same PPU-last instrumentation.
    for g in range(906,958):
        rows=[r for r in cpu[g] if r['op']==3]
        load,upload,final,ack,reveal=[one(rows,k) for k in ('load','upload165_entry','final212','ack','reveal')]
        enter=one([r for r in events if r['generation']==g],'output_enter531')['clock']
        active=Counter();sizes=Counter();counts=Counter();raw=False
        starts={}
        for r in dma[g]:
            if r['event']=='raw_enter':raw=True
            elif r['event']=='raw_done':raw=False
            elif r['event']=='dma':
                kind=('palette' if r['port']==34 else 'OAM' if r['port']==4 else
                      'raw' if raw else 'map' if r['src']&0x7000==0x5000 else 'tile')
                starts[r['clock']]=(kind,r['bytes'])
        current=None
        waits=[];wait=None
        for r in rows:
            event=r['event']
            if event=='ppu_dma':
                assert current is None
                kind,n=starts[r['clock']];assert n==r['value']
                current=(kind,n,r['clock'])
            elif event=='ppu_last':
                assert current is not None
                kind,n,t=current;active[kind]+=r['clock']-t;sizes[kind]+=n;counts[kind]+=1;current=None
            elif event=='wait169':
                assert wait is None
                wait=r['clock']
            elif wait is not None and (event.startswith('wait_return_') or event=='final_upload212_same_blank212'):
                waits.append(dict(start=wait,end=r['clock'],final=wait>=final['clock']))
                wait=None
        assert current is None and wait is None
        checks=upload['clock']-load['clock']
        wait_ticks=sum(w['end']-w['start'] for w in waits)
        total=ack['clock']-load['clock']
        other=total-checks-wait_ticks-sum(active.values())
        assert other>=0 and enter<=load['clock']
        result[g]=dict(output_to_head_ms=ms(load['clock']-enter),SEAL_to_ACK_ms=ms(total),
                       checks_ms=ms(checks),serviced_VBlank_wait_ms=ms(wait_ticks),
                       DMA_ms={k:ms(v) for k,v in active.items()},DMA_B=sizes,DMA_count=counts,
                       other_setup_control_ms=ms(other),final_wait_count=sum(w['final'] for w in waits),
                       final_wait_ms=ms(sum(w['end']-w['start'] for w in waits if w['final'])),
                       head_to_reveal_VB=reveal['frame']-load['frame'],final_entry_line=final['line'])
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','plans','calendar','arm','client','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--tag',choices=('raw','reg','cursor'),default='raw')
    a=p.parse_args();cal=Calendar(a.calendar);phases=[]
    for i in (1,2):
        base=a.traces/f'nes-first539-row{i}'
        new=a.traces/f'nes-dma542-{a.tag}{i}'
        r=inspect_run(new,a.plans,cal,base,sha(a.arm/'obj-nes-100/firmware.stm'),sha(a.client/'sink165.sfc'))
        previous=read(Path(__file__).resolve().parents[1]/'analysis/first539-verification.json')['phases'][i-1]['row']
        assert all(sha(base/f)==v for f,v in previous['pins'].items())
        r['last_ACK_delta_ms']=ms(r['last_ACK']-previous['last_ACK'])
        r['later_BG_windows']=[g for g,b in r['BG'].items() if b['relative_window']>previous['BG'][str(g)]['relative_window']]
        r['dense_delta_ms']=r['dense_ms']-previous['dense_ms']
        r['base_partition']=partition(base);r['candidate_partition']=partition(new)
        r['gate']=r['last_ACK_delta_ms']<0 and r['dense_delta_ms']<0 and not r['later_BG_windows'] and not any(r['waits'].values())
        phases.append(r)
    a.out.write_text(json.dumps(dict(phases=phases,gate=all(r['gate'] for r in phases),
        scope='Actual ARM/SPI/IRQ/65816 continuous simulation; repeated boot ROM calendar, not physical FPS. Wait includes serviced polling; DMA active measured start to last byte.'),indent=2)+'\n')
