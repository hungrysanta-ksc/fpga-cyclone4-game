# SPDX-License-Identifier: MIT
"""Attribute the 3200 range and check actual last returns, DMA and display."""
import argparse
import json
from collections import Counter
from pathlib import Path
from analyze_nes_map628 import normalize
from analyze_nes_window756 import summarize
from analyze_nes_rows757 import ranges
from analyze_nes_owner739 import read,sha,ms


def costs(folder):
    events=[e for e in read(folder/'events.json') if e.get('generation')==957]
    writes=[e for e in events if e['event']=='map_store757' and 3200<=e['offset']<3392]
    lo,hi=writes[0]['clock'],writes[-1]['clock']
    spans=[]
    for e in events:
        if e['event'] not in ('SPI','work758'):continue
        left=max(lo,e['start']);right=min(hi,e['clock'])
        if left>=right:continue
        name=e['opcode'] if e['event']=='SPI' else e['name']
        spans.append((left,right,name))
    boundaries=sorted({lo,hi}|{x for a,b,_ in spans for x in (a,b)})
    costs=Counter()
    for left,right in zip(boundaries,boundaries[1:]):
        active={name for a,b,name in spans if a<=left and right<=b}
        spi=[k for k in active if k.startswith('0x')]
        assert len(spi)<=1
        if spi:name=spi[0]
        elif 'map_word185' in active:name='map_writer'
        elif 'nes_resident211_slot' in active:name='slot'
        else:name='other'
        costs[name]+=ms(right-left)
    assert abs(sum(costs.values())-ms(hi-lo))<1e-8
    return dict(total_ms=ms(hi-lo),exclusive_ms=costs,
                calls_overlapping=dict(Counter(n for a,b,n in spans)),store_count=len(writes))


def causal_budget(folder,m,detail):
    # Remove the entire observed critical span from all following release times;
    # keep the real FIFO order, consumption service, E1 charges and prior events.
    # The counterfactual never changes production firmware or measures new FPS.
    events=read(folder/'events.json')
    touched=[e['clock'] for e in events if e.get('generation')==957 and e['event']=='map_store757'
             and 3200<=e['offset']<3392]
    deadline=m['first248'][1];begin=ms(min(touched)-deadline);end=ms(max(touched)-deadline)
    def reduced(t):return t-max(0,min(t,end)-begin)
    ideal=-1e10
    consumer=-1e10
    for pkt in m['page']:
        ready=reduced(detail['rows'][pkt['offset']]['last_write'])
        if ready>=ideal:
            critical_offset=pkt['offset']
        ideal=max(ready,ideal)+ms(pkt['push']-pkt['start'])
        consumer=max(ideal,consumer)+ms(pkt['retired']-pkt['accepted'])
    return dict(zero_3200_slot_write_and_SPI_E1_end_ms=ideal,as_observed_service_return_ms=consumer,critical_offset=critical_offset)

def analyze(temp,probe):
    result=dict(phases={},selected='753',guards={})
    modes=('control','word','compact','tail','burst')
    for n in (1,2):
        base=temp/f'nes-credit753-prefix{n}';work,_=normalize(base)
        ref=summarize(base,base,n,work)
        rows=result['phases'][n]={}
        for mode in modes:
            d=temp/f'nes-tail758-{mode}{n}'
            if mode=='word' and not (d/'joint.json').is_file():
                d=temp/f'nes-tail758-word2nd{n}'  # Original probe assumed a non-inlined writer.
            metrics=summarize(d,base,n,work,ordered_page=False)
            detail=ranges(d,metrics)
            arm=probe.parent/'nes-credit753/arm-prefix' if mode=='control' else probe/f'arm-{mode}'
            binary=arm/'src/obj-nes-100/firmware.stm'
            assert sha(binary)==metrics['firmware']
            metrics.update(stage3200=costs(d),budget=causal_budget(d,metrics,detail),Flash_B=binary.stat().st_size,
                           ordered_offsets=[r['offset'] for r in metrics['page']],
                           tail={k:detail['rows'][k] for k in (3200,3392)},
                           last_return_offset=metrics['page'][-1]['offset'],
                           post956_return_ms=metrics['last_map_after_956_ACK_ms'],
                           dense_delta_ms=metrics['mean_ms']-ref['mean_ms'],
                           ACK_delta_ms=ms(metrics['ACK']-ref['ACK']))
            metrics['BSS_B']=int((arm/'size.log').read_text().splitlines()[-1].split()[2])
            metrics['qualified']=(metrics['safe_schedule'] and metrics['last_map_late_ms']<=0 and
                                  metrics['intervals'][957]==2 and metrics['dense_delta_ms']<0 and
                                  metrics['ACK_delta_ms']<0 and metrics['Flash_B']<=212992)
            if mode=='control':
                assert all(metrics[k]==ref[k] for k in ('page','intervals','ACK','mean_ms','map_DMA','BG','OBJ'))
            rows[mode]=metrics
    for mode in modes[1:]:
        guard=read(probe/f'guards-{mode}.json')
        assert guard['firmware']==guard['menu']['firmware']==result['phases'][1][mode]['firmware']
        result['guards'][mode]=guard
        if all(r[mode]['qualified'] for r in result['phases'].values()):result['selected']=mode
    result['receiver_guards']={}
    for n in (1,2):
        row=result['phases'][n]['tail']
        checks={}
        for fault in ('before','during','head','stale'):
            test=read(temp/f'nes-tail758-tail{n}-{fault}/verified751.json')
            assert test['client']==row['ROM'] and test['commits']==(53 if fault=='head' else 52)
            assert test['source']==23680 and test['size']==384
            checks[fault]=test
        result['receiver_guards'][n]=checks
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('temp','probe','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+'\n',encoding='utf8',newline='\n')
