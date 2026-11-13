# SPDX-License-Identifier: MIT
"""Compare linked schedules against the same-phase 753 baseline and isolate offer-only replays."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_bg750 import counters
from analyze_nes_owner739 import csv_groups, ms, read, sha
from analyze_nes_static751 import phase


def summarize(folder):
    win=csv_groups(folder/'window.csv')
    dma=counters(folder/'dma748.csv')
    def ev(g,event):
        return next(r for r in win[g] if r['event']==event and r['op']==3)
    row={}
    for g in range(952,958):
        prev,load,show,ack=(ev(g-1,'reveal'),ev(g,'load'),ev(g,'reveal'),ev(g,'ack'))
        later=[r for r in win[g] if r['clock']>load['clock']]
        row[g]=dict(seal=load,display=show,interval=show['frame']-prev['frame'],
                    after_previous_ms=ms(load['clock']-prev['clock']),ack=ack['clock'],
                    upload_first_wait_ms=ms(next(r['clock'] for r in later if r['event']=='wait169')-load['clock'])
                    if any(r['event']=='wait169' for r in later) else None,
                    remaining_dma_B=[r['value'] for r in later if r['event']=='ppu_dma'])
    maps={}
    for g,src in ((952,0xd800),(957,0x5800)):
        maps[g]=next((r for r in dma if r['g']==g and r['source']==src and r['bytes']==1536
                      and r['clock']<row[g]['seal']['clock']),None)
    obj=next(r for r in dma if r['g']==957 and r['source']==19104 and r['bytes']==288)
    m=maps[957]
    def dma_frame(clock):
        e=next(r for r in win[957] if r['event']=='ppu_dma' and r['clock']>=clock)
        assert e['clock']-clock<120
        return e['frame']
    grants=list(csv.DictReader((folder/'budget685.csv').open()))
    # Anchor the previous map deadline to an actual beam latch in the first
    # VBlank, avoiding estimates from average period or frame wrap.
    anchor=next(r for r in grants if int(r['generation'])==957)
    limit=int(anchor['latch_clock'])+(249-int(anchor['line']))*1364-int(anchor['h'])
    last=next(r for r in reversed(win[957]) if r['event']=='ack' and r['section']==2)
    raw=list(csv.DictReader((folder/'seal528.csv').open()))
    def raw_clock(event,after):
        return next(int(r['clock']) for r in raw if r['g']=='957' and r['event']==event
                    and int(r['clock'])>after)
    raw_start=raw_clock('raw_enter',row[957]['seal']['clock'])
    return dict(frames=row,mean_ms=ms(ev(957,'reveal')['clock']-ev(951,'reveal')['clock'])/6,
                ack=row[957]['ack'],map=maps,OBJ=obj,
                OBJ_same_blank=bool(m and dma_frame(m['clock'])==dma_frame(obj['clock'])),
                raw_clocks=raw_clock('raw_done',raw_start)-raw_start,last_map_ack=last['clock'],
                first_grant=anchor,first_blank_end248_clock=limit,map_late_ms=ms(last['clock']-limit),
                pins={f:sha(folder/f) for f in ('window.csv','seal528.csv','dma748.csv','budget685.csv')})


def analyze(t,probe):
    result=dict(reference='753 prefix',scope='Linked ARM and reset 65816; SPI/IRQ/ROM timing model. Replays only retime output offers.',
                reference_phases={},linked={},replay={})
    client=probe.parent/'nes-static751/sharedfast'
    prior=read(Path('analysis/credit753-verification.json'))['variants']['prefix']
    for n in (1,2):
        folder=t/f'nes-credit753-prefix{n}'
        base=summarize(folder)
        assert base['ack']==prior[str(n)]['timing']['ACK']
        assert all(v['interval']==3 for v in base['frames'].values())
        assert min(base['frames'],key=lambda g:base['frames'][g]['after_previous_ms'])==957
        rows=csv_groups(folder/'window.csv')
        start=next(e['clock'] for e in rows[956] if e['event']=='ack' and e['op']==3)
        end=base['last_map_ack']
        wire={}
        for e in read(folder/'events.json'):
            if e['event']!='SPI':continue
            occupied=min(end,e['clock'])-max(start,e['start'])
            if occupied<=0:continue
            key=e['opcode']
            wire[key]=wire.get(key,0)+occupied
        available=base['first_blank_end248_clock']-start
        base['bus_budget']=dict(begin=start,end=end,occupied_clocks=wire,
            available_ms=ms(available),SPI_ms=ms(sum(wire.values())),excess_ms=ms(sum(wire.values())-available))
        result['reference_phases'][n]=base
        for k in ('section','geometry','both','shared','raw','combined'):
            f=t/f'nes-seal754-{k}{n}'
            arm=probe.parent/'nes-credit753/arm-prefix' if k=='raw' else probe/('arm-shared' if k=='combined' else f'arm-{k}')
            image=arm/'src/obj-nes-100/firmware.stm'
            rom=probe/'raw' if k in ('raw','combined') else client
            j=phase(t,'sharedfast',n,folder=f,client=rom,firmware=sha(image))
            timing=summarize(f)
            gain=timing['mean_ms']<base['mean_ms'] and timing['ack']<base['ack']
            passes=(gain and timing['frames'][957]['interval']==2 and j['guarded_schedule']
                    and j['E8_start']<=j['E8_749_start'] and j['E8_end']<=j['E8_749_end']
                    and j['OBJ']['line']<=256 and image.stat().st_size<=212992)
            result['linked'].setdefault(k,{})[n]=dict(timing=timing,flash=image.stat().st_size,
                dense_delta_us=1000*(timing['mean_ms']-base['mean_ms']),ACK_delta_ms=ms(timing['ack']-base['ack']),
                guards=j['guarded_schedule'],intervals=j['intervals'],final_wait957=j['final_wait957'],
                E8_delta_749=j['E8_delta_clocks'],E8_end_delta_749=j['E8_end']-j['E8_749_end'],
                public951=j['line951'],passes=passes,firmware=sha(image),client=sha(rom/'sink165.sfc'),pins=j['pins'])
        for tag in ('control0','tail8500','all8500','all16640','gap16640'):
            f=t/f'nes-seal754-replay-{tag}-{n}'
            audit=read(f/'audit711.json')
            timing=summarize(f)
            assert audit['same_pixels'] and audit['prefix_exact'] and audit['full_CRC_coverage_ACK']
            if tag=='control0':assert all(base[k]==v for k,v in timing.items())
            result['replay'].setdefault(tag,{})[n]=dict(timing=timing,pins=audit['pins'],
                SEAL_advance_ms=audit['metrics']['957']['seal_load_advance_ms'],
                ACK_delta_ms=ms(timing['ack']-base['ack']),dense_delta_ms=timing['mean_ms']-base['mean_ms'])
    from analyze_nes_credit753 import partition
    for n in (1,2):
        b=t/f'nes-credit753-prefix{n}'
        f=t/f'nes-seal754-shared{n}'
        initial,changed=partition(b),partition(f)
        result['linked']['shared'][n]['input']=dict(before=initial['blocks_before_ACK'],
            after=changed['blocks_before_ACK'],source_to_planner_delta_ms=ms(changed['total']-initial['total']))
        receipt=next(r['clock'] for r in csv_groups(b/'window.csv')[956] if r['event']=='ack' and r['op']==3)
        events=read(b/'events.json')
        commit=next(e['clock'] for e in events if e['generation']==957 and e.get('opcode')=='0xd3')
        replay=t/f'nes-seal754-replay-gap16640-{n}'
        with (replay/'admission711.csv').open() as stream:
            admissions=[r for r in csv.DictReader(stream) if r['g']=='957']
        result['replay']['gap16640'][n]['availability_ms_after_956_ACK']=dict(
            replay_first_BG_admitted=ms(int(admissions[2]['admit'])-receipt),
            real_input_commit=ms(commit-receipt),real_planner=ms(initial['planner']-receipt))
        result.setdefault('consumer_guards',{})[n]={
            fault:read(t/f'nes-seal754-sharedguard-{n}-{fault}/verified751.json')
            for fault in ('before','during','head','stale')}
    result['combined_consumer_guards']={n:{
        fault:read(t/f'nes-seal754-combinedguard-{n}-{fault}/verified751.json')
        for fault in ('before','during','head','stale')} for n in (1,2)}
    result['arm_guards']=read(probe/'guards-shared.json')
    from types import SimpleNamespace
    from check_nes_seal754_raw import verify
    result['raw_STOP']=[verify(SimpleNamespace(trace=t/f'nes-seal754-raw{n}',out=t/f'nes-seal754-rawguard{n}-{r}',row=r))
                        for n in (1,2) for r in (0,2)]
    result['rom']=read(probe/'raw/build.json')
    result['qualified']=[k for k,v in result['linked'].items() if all(r['passes'] for r in v.values())]
    result['selected']=result['qualified'][0] if result['qualified'] else '753 prefix'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+'\n',encoding='utf8')
