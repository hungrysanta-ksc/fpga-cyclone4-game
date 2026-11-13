# SPDX-License-Identifier: MIT
"""Partition the 957 source-to-planner interval without double-counting prefetch."""
import argparse
from collections import Counter
import json
from pathlib import Path

from analyze_nes_credit752 import csv_groups, phase, read, sha


def partition(folder):
    events=read(folder/'events.json')
    i=next(i for i,x in enumerate(events) if x['event']=='source_begin' and x['generation']==957)
    j=next(i for i,x in enumerate(events[i:],i) if x['event']=='planner_enter' and x['generation']==957)
    group=events[i:j+1]
    start,stop=group[0]['clock'],group[-1]['clock']
    spi=[x for x in group if x['event']=='SPI']
    # A first D0 can initiate source_begin from inside the endpoint.
    # Clip all charged intervals to this measured span.
    intervals=[]
    def charge(key,a,b):
        a=max(start,a);b=min(stop,b)
        if b>a:intervals.append((a,b,key))
    blocks=[]
    for idx,x in enumerate(spi):
        op=x['opcode']
        charge(op,x['start'],x['clock'])
        if op=='0xd1':
            pop,confirm=spi[idx+1:idx+3]
            assert (pop['opcode'],confirm['opcode'])==('0xd2','0xd0')
            charge('restore_and_prepare_POP',x['clock'],pop['start'])
            blocks.append(dict(start=x['start'],bytes=x['bytes'],D1=x['clock']-x['start'],
                               restore_to_POP=pop['start']-x['clock'],confirmed=confirm['clock']))
    polls=[x for x in spi if x['opcode']=='0xe0' and x['generation']==956]
    ack=next(x['clock'] for x in csv_groups(folder/'window.csv')[956] if x['event']=='ack' and x['op']==3)
    waits=[]
    for x in group:
        if x['event']!='input682_return' or x['begin']['reason']!=2 or x['begin']['progress']:continue
        a,b=x['begin']['clock'],x['clock']
        if any(v['start']<b and v['clock']>a for v in spi):continue
        charge('quiet_final_callback',a,b)
        waits.append(b-a)
    totals=Counter()
    prev=start
    for a,b,key in sorted(intervals):
        assert a>=prev-1e-5,(a,b,prev,key)
        totals[key]+=b-a
        prev=b
    totals['other_ARM_IRQ_and_boundaries']=stop-start-sum(totals.values())
    assert totals['other_ARM_IRQ_and_boundaries']>=0 and len(blocks)==17
    return dict(start=start,planner=stop,total=stop-start,costs=totals,blocks=blocks,
                SPI_counts=Counter(x['opcode'] for x in spi),quiet_callbacks=waits,
                previous_final_ACK=ack,blocks_before_ACK=sum(x['confirmed']<=ack for x in blocks),
                previous_SEAL_E0=[dict(start=x['start'],end=x['clock'],retired=int(x['reply'][10:14],16)) for x in polls])


def analyze(temp,probe,policies):
    result=dict(stage=753,client='751 sharedfast',board='707D',baseline='752 mapobj',
                costs={},variants={},passed_both=[],guards={},faults={})
    client=probe.parent/'nes-static751/sharedfast'
    image=sha(client/'sink165.sfc')
    old_result=read(Path('analysis/credit752-verification.json'))
    assert image==old_result['ROM_SHA256']
    result.update(ROM_SHA256=image,physical_ROM_free_B=old_result['physical_ROM_free_B'],
                  scope='Full ARM link and reset-booted 53-frame 65816 execution; modeled SPI/IRQ/ROM, no new hardware test.')
    for n in (1,2):
        ref=partition(temp/f'nes-obj749-page{n}')
        old=partition(temp/f'nes-credit752-mapobj{n}')
        costs={k:old['costs'].get(k,0)-ref['costs'].get(k,0) for k in ref['costs'].keys()|old['costs'].keys()}
        result['costs'][n]=dict(reference749=ref,baseline752=old,delta=costs)
        assert abs(old['total']-ref['total']-sum(costs.values()))<0.01
    assert round(sum(result['costs'][1]['delta'].values()))==5906
    for k in policies:
        fw=probe/f'arm-{k}/src/obj-nes-100/firmware.stm'
        v=result['variants'][k]={}
        g=read(probe/f'guards-{k}.json')
        assert sha(fw)==g['firmware']==g['menu']['firmware'] and len(g['initial_batch'])==6
        result['guards'][k]=g
        if k=='inputcrc':assert g['bad_cached_status_bits']==56
        if k.startswith('prefix'):assert [z['reads'] for z in g['prefix_budget']]==[8,7,7,7]
        for n in (1,2):
            folder=temp/f'nes-credit753-{k}{n}'
            timeline=phase(temp,'sharedfast',n,folder=folder,client=client,firmware=sha(fw))
            costs=partition(folder)
            deadline=(timeline['E8_delta_clocks']<=0 and timeline['E8_end']<=timeline['E8_749_end'])
            obj=timeline['margin_to_258'] is not None and timeline['OBJ']['line']<=256
            gain=timeline['ACK_delta']<0 and timeline['dense_delta_us']<0
            # E8 may pass only because an earlier display moved one VBlank.
            # Keep the 956-relative query offset alongside the reset clock.
            explicit=bool(deadline and obj and gain and all(timeline['long_map'].values()) and
                          timeline['order'] and timeline['final_wait957']==0)
            v[n]=dict(requested_metrics=explicit,firmware=sha(fw),flash=fw.stat().st_size,source=costs,timing=timeline,
                      passed=deadline and obj and gain and timeline['guarded_schedule'] and fw.stat().st_size<=212992)
            for fault in ('before','during','head','stale'):
                f=temp/f'nes-credit753-guard-{k}{n}-{fault}/verified751.json'
                if f.exists():
                    replay=read(f)
                    assert replay['fault']==fault and replay['client']==sha(client/'sink165.sfc')
                    assert replay['source']==19104 and replay['size']==288
                    assert replay['commits']==(53 if fault=='head' else 52)
                    result['faults'][f'{k}{n}-{fault}']=replay
        if all(x['passed'] for x in v.values()):
            result['passed_both'].append(k)
            assert all(f'{k}{n}-{fault}' in result['faults'] for n in (1,2) for fault in ('before','during','head','stale'))
    # Compare each tested ELF, including diagnostics above the flash limit.
    # Keep full-pass candidates distinct from changes which only speed up 957.
    result['selected']=next((k for k in ('prefix','sealcrc') if k in result['passed_both']),None)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--policies',nargs='+',default=['ready','geometry','one','large','inputcrc','sealcrc','objburst','prefix','prefixcrc'])
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe,a.policies),indent=2)+'\n',encoding='utf8',newline='\n')
