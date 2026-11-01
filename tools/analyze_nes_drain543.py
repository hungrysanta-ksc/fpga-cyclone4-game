# SPDX-License-Identifier: MIT
"""Separate the trimmed-counter control from the post-map drain on both ROM phases."""
import argparse
import json
from collections import Counter
from pathlib import Path
from analyze_nes_dma542 import partition
from analyze_nes_phase537 import Calendar, csv_groups, read, sha, ms
from analyze_nes_seal538 import inspect_run

ROOT=Path(__file__).resolve().parents[1]


def map_gap(folder):
    packets=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    cpu=csv_groups(folder/'window.csv');events=read(folder/'events.json');result={}
    for g in range(905,958):
        mine=[(i+1,r[1],bytes.fromhex(r[2])) for i,r in enumerate(packets) if int.from_bytes(bytes.fromhex(r[2])[8:10],'little')==g]
        maps=[r for r in mine if r[2][0] in (2,4) and r[2][1]==2]
        if not maps:continue
        idx,arrived,_=maps[-1]
        first=next(r for r in mine if r[2][0] in (2,4,5,8) and r[2][1]>=3)
        ack=next(r for r in cpu[g] if r['index']==idx and r['event']=='ack')
        early=Counter();within=Counter();kind=None;in_gap=False
        for r in cpu[g]:
            if r['event']=='idle524':
                kind='map' if r['value']>=65536 else 'tile';in_gap=ack['clock']<=r['clock']<first[1]
            elif r['event']=='ppu_dma' and r['op']==-1:
                assert kind is not None
                early[kind]+=r['value']
                if in_gap:within[kind]+=r['value']
            elif r['event']=='ppu_last' and r['op']==-1:kind=None
        polls=[r for r in events if r['generation']==g and r.get('opcode')=='0xe0' and arrived<=r['start']<first[1]]
        result[g]=dict(last_map_arrival=arrived,last_map_ACK=ack['clock'],first_later_ordinary_arrival=first[1],
                       producer_gap_ms=ms(first[1]-arrived),after_map_ACK_gap_ms=ms(max(0,first[1]-ack['clock'])),
                       E0_between_arrivals=len(polls),early_DMA_B=early,DMA_started_in_empty_gap_B=within)
    return result


def delta(row,base):
    return dict(last_ACK_ms=ms(row['last_ACK']-base['last_ACK']),dense_ms=row['dense_ms']-base['dense_ms'],
                dense_VB=row['dense_VB']-base['dense_VB'],
                later_BG_windows=[g for g,v in row['BG'].items() if v['relative_window']>base['BG'].get(g,base['BG'].get(str(g)))['relative_window']],
                SPI_B={k:row['SPI_B'].get(k,0)-base['SPI_B'].get(k,0) for k in set(row['SPI_B'])|set(base['SPI_B'])},
                ARM_instructions=row['ARM_instructions']-base['ARM_instructions'],IRQ=row['IRQ']-base['IRQ'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','plans','calendar','base_arm','arm','client','out'):p.add_argument('--'+n.replace('_','-'),type=Path,required=True)
    a=p.parse_args();cal=Calendar(a.calendar);phases=[]
    old=read(ROOT/'analysis/first539-verification.json')
    for phase in (1,2):
        ref=a.traces/f'nes-first539-row{phase}';previous=old['phases'][phase-1]['row']
        assert all(sha(ref/n)==v for n,v in previous['pins'].items())
        measured={}
        for tag,arm in [('base',a.base_arm),('drain',a.arm)]:
            folder=a.traces/f'nes-drain543-{tag}{phase}'
            r=inspect_run(folder,a.plans,cal,ref,sha(arm/'obj-nes-100/firmware.stm'),sha(a.client/'sink165.sfc'))
            r['partition']=partition(folder);r['map_gap']=map_gap(folder)
            r['versus_MMC540']=delta(r,previous)
            measured[tag]=r
        comparison=delta(measured['drain'],measured['base'])
        combined=measured['drain']['versus_MMC540']
        phases.append(dict(phase=phase,**measured,drain_effect=comparison,
                           gate=all(x['last_ACK_ms']<0 and x['dense_VB']<0 and not x['later_BG_windows'] for x in (comparison,combined)) and not any(measured['drain']['waits'].values())))
    a.out.write_text(json.dumps(dict(phases=phases,gate=all(p['gate'] for p in phases),
        scope='Shared workload, two starts, actual linked ARM/SPI/SysTick/65816; repeated ROM calendar. Counter-only control is separate. Gap includes preparation and bulk service, not pure drain duration.'),indent=2)+'\n')
