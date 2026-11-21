"""Correlate the physical map DMA and fully retired strip identity with the palette wait."""
import argparse
import csv
import json
from pathlib import Path

from check_nes_strip869 import compare, publication_cost
from check_nes_game478 import crc
from analyze_nes_map830 import load, packets, window


def evidence(folder):
    trace=window(folder)
    g=936
    prev=next(e for e in trace if e['g']==g-1 and e['event']=='reveal')
    local=[e for e in trace if e['g']==g]
    palette=next(e for e in local if e['event']=='load' and e['section']==3)
    seal=next(e for e in local if e['event']=='load' and e['op']==3)
    visible=next(e for e in local if e['event']=='reveal')
    data=packets(folder)
    spi=[e for e in load(folder/'events.json') if e.get('event')=='SPI']
    heads=[e for e in spi if e['opcode']=='0xe1']
    first=heads[palette['index']-1]['start']
    strip=[e for e in local if e['event']=='ack' and e['op']==10]
    real_map=[e for e in local if e['event']=='ppu_dma' and e['op']!=3 and e['value']==1472]
    complete=None
    checked=[]
    if strip and real_map:
        assert len(real_map)==len(strip)==1 and real_map[0]['clock']>=strip[0]['clock']
        last=next(e for e in local if e['clock']>=real_map[0]['clock'] and e['event']=='ppu_last')
        with (folder/'progress680.csv').open() as f:
            pulse=next(r for r in csv.DictReader(f) if int(r['clock'])>=last['clock'])
        assert int(pulse['retired'])==int(pulse['sent'])==strip[0]['index']
        complete=int(pulse['clock'])
        b=data[strip[0]['index']-1]
        for e in spi:
            if e['opcode']!='0xe0' or not complete<=e['clock']<first:continue
            r=bytes.fromhex(e['reply'])
            assert len(r)==20 and r[1]==0xf7 and crc(r[1:19],8,7,0)==r[19]
            if r[2]==10 and r[3:5]==r[5:7] and r[7:17]==bytes((0,b[0]))+b[2:10]:
                assert r[17:19]==bytes.fromhex('659a')
                assert int.from_bytes(r[3:5],'big')==strip[0]['index']%65536
                checked.append(round(e['clock']))
    cost=publication_cost(folder)[g]
    with (folder/'seal528.csv').open() as f:
        checks=[(r['event'],int(r['line'])) for r in csv.DictReader(f)
                if int(r['g'])==g and r['event'] in ('final_credit','latch')]
    return dict(gap=visible['frame']-prev['frame'],previous=[prev['frame'],prev['line']],
                visible=[visible['frame'],visible['line']],map_DMA_start=real_map[0]['clock'] if real_map else None,
                strip_retire=[[e['frame'],e['line']] for e in strip], SEAL_checks=checks,
                full_map_DMAs=[dict(clock=e['clock'],at_SEAL=e['op']==3,frame=e['frame'],line=e['line'])
                               for e in local if e['event']=='ppu_dma' and e['value']==1472],
                map_progress_clock=complete, checked_strip_E0=checked, palette_start=round(first),
                SEAL=[seal['clock'],seal['frame'],seal['line']], costs=cost)


def report(temp,work,tag):
    d=compare(temp,work,tag)
    guards=load(work/'guards.json')
    assert guards['client']==d['client'] and guards['source_tag']==tag
    d['consumer_guards']=guards
    boundary=load(work/'begin.json')
    d['begin_guards']=boundary['begin']
    d['strip_E0_guards']=boundary['strip_E0']
    assert all(ok==(k=='valid') for k,ok in d['strip_E0_guards'].items())
    assert all(v['progress_cleared'] and v['accepted']==(k!='stale')
               for k,v in d['begin_guards'].items())
    d['generation936']={i:{k:evidence(temp/f'nes-tile821-demo-jointmirror-p{i}-{k}')
                            for k in ('866-on','869-credit',tag)} for i in (1,2)}
    for i in (1,2):
        assert d['scenes'][f'demo-{i}']['candidate']['warm_map_wire_B']==40158
        assert d['scenes'][f'demo-{i}']['candidate']['strips']==19
    d['gate']={
        'flash':d['flash_B']<=212992,
        'checked_advance_map_DMA':all(d['generation936'][i][tag]['checked_strip_E0'] for i in (1,2)),
        '936_at_most_three':all(d['generation936'][i][tag]['gap']<=3 for i in (1,2)),
        'opening_703':all(d['scenes'][f'opening-{i}']['candidate']['opening_marks']['910']
                          <=d['scenes'][f'opening-{i}']['reference']['opening_marks']['910'] for i in (1,2)),
        'dense_intervals_and_ACK':all(d['scenes'][f'demo-{i}']['ACK_delta_clocks']<0 and
                          d['scenes'][f'demo-{i}']['candidate']['after_two_VBlanks']<
                          d['scenes'][f'demo-{i}']['reference']['after_two_VBlanks'] for i in (1,2))}
    return d


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','work'):p.add_argument(k,type=Path)
    p.add_argument('tag')
    p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.work,a.tag),indent=2)+'\n')
