# SPDX-License-Identifier: MIT
"""Compare map-ready/credit/VBlank on the same trimmed-counter control and two starts."""
import argparse,json
from pathlib import Path
from analyze_nes_frontier536 import ledger
from analyze_nes_dma542 import partition
from analyze_nes_phase537 import Calendar,read,sha,csv_groups,one,ms
from analyze_nes_seal538 import inspect_run
from analyze_nes_drain543 import delta

ROOT=Path(__file__).resolve().parents[1]

def decode_windows(folder,audit,windows):
    """Clip actual packet code boundaries to the last eligible pre-SEAL blank."""
    proof=read(audit/'audit.json');assert proof['frames']==53 and proof['trace']==sha(folder/'window.csv')
    marks=csv_groups(audit/'decode544.csv');cpu=csv_groups(folder/'window.csv')
    events=read(folder/'events.json');out={}
    for g in (951,957):
        start=one([e for e in events if e['generation']==g],'source_begin')['clock']
        w=max(windows[g]['windows'],key=lambda r:r['open_ms']);totals={}
        for packet in w['head_service']:
            idx=packet['index'];c=[r for r in cpu[g] if r['index']==idx]
            s={r['event']:r['clock'] for r in marks[g] if r['index']==idx}
            # Use the packet index: header scratch still describes its predecessor at header entry.
            load=one(c,'load')['clock'];ack=one(c,'ack')['clock']
            if not {'header','data','data_size_ok','accepted','reply'}<=s.keys():
                assert packet['section']!=5
                totals['other_packet']=totals.get('other_packet',0)+packet['ms'];continue
            body=min(s[n] for n in ('literal1814','repeat1814','zero_chunk516') if n in s)
            edges=[load,s['header'],s['data'],s['data_size_ok'],body,s['accepted'],ack]
            assert edges==sorted(edges)
            for k,l,h in zip(('select','header_dispatch','data_bounds','mark_and_address','payload','accept_and_ACK'),edges,edges[1:]):
                dt=max(0,min(ms(h-start),w['close_ms'])-max(ms(l-start),w['open_ms']))
                totals[k]=totals.get(k,0)+dt
        assert abs(sum(totals.values())-sum(r['ms'] for r in w['head_service']))<1e-6
        out[g]=dict(packets=len(w['head_service']),occupied_ms=totals)
    return dict(trace=proof['trace'],markers_SHA256=sha(audit/'decode544.csv'),last_preSEAL_VBlank=out)

def analyze(a):
    cal=Calendar(a.calendar);old=read(ROOT/'analysis/drain543-verification.json');phases=[]
    assert sha(a.client/'sink165.sfc')==read(ROOT/'analysis/first539-verification.json')['client']
    for i in (1,2):
        measured={}
        variants=[('base',a.base_arm,f'nes-drain543-base{i}'),('front',a.arm,f'nes-front544-final{i}')]
        if a.after_tile_arm:variants.append(('tail',a.after_tile_arm,f'nes-front544-tail{i}'))
        for name,arm,trace in variants:
            folder=a.traces/trace;ref=a.traces/f'nes-drain543-base{i}'
            assert all(sha(ref/n)==s for n,s in old['phases'][i-1]['base']['pins'].items())
            r=inspect_run(folder,a.plans,cal,ref,sha(arm/'obj-nes-100/firmware.stm'),sha(a.client/'sink165.sfc'))
            audit=a.traces/f'nes-front544-audit-{name}{i}'
            proof=read(audit/'audit.json')
            assert proof['frames']==53 and proof['trace']==sha(folder/'window.csv')
            assert sha(audit/'tile532.csv')==sha(folder/'tile532.csv')
            r['independent_replay']=proof
            r['selector_SHA256']=sha(audit/'selector536.csv')
            r['map_VBlank']=ledger(folder,audit,targets=((951,2560),(957,2048)))
            if name=='base' and a.decode:
                r['decode']=decode_windows(folder,a.traces/f'nes-front544-audit-decode-base{i}',r['map_VBlank'])
            r['partition']=partition(folder)
            cpu=csv_groups(folder/'window.csv')
            r['targets']={}
            for g in (951,957):
                current=[e for e in cpu[g] if e['op']==3]
                previous=one([e for e in cpu[g-1] if e['op']==3],'reveal')
                reveal=one(current,'reveal');ack=one(current,'ack')
                r['targets'][g]=dict(display_interval_ms=ms(reveal['clock']-previous['clock']),
                                     display_VB=reveal['frame']-previous['frame'],last_ACK=ack['clock'],
                                     final_wait_count=r['partition'][g]['final_wait_count'])
            joint=read(folder/'joint.json')
            r['observed_stack_low']=joint['observed_stack_low']
            r['IRQ_boundary_lateness_masterclocks']=joint['IRQ_boundary_lateness_masterclocks']
            es=read(folder/'events.json');ready={}
            for g in range(905,958):
                group=[e for e in es if e['generation']==g]
                frozen,=[e for e in group if e['event']=='bg_map_frozen']
                end,=[e for e in group if e['event']=='end_enter']
                prepare,=[e for e in group if e['event']=='prepare_enter']
                edge=frozen['clock']
                if name!='base':
                    offer,=[e for e in group if e['event']=='frozen_offer544']
                    assert offer['map_SHA256']==frozen['sha256']
                    edge=offer['clock']
                maps=[e for e in group if e['event']=='map_packet_enter' and e['early'] and edge<e['clock']<end['clock']]
                ready[g]=dict(map_SHA256=frozen['sha256'],frozen_offer=edge,map_snapshot_before_OAM=frozen['clock'],prepared=prepare['clock'],END_enter=end['clock'],
                              new_early_offsets=[e['offset'] for e in maps],new_early_clocks=[e['clock'] for e in maps])
            r['frozen_map']=ready;measured[name]=r
        for g in range(905,958):
            assert all(measured['base']['frozen_map'][g]['map_SHA256']==v['frozen_map'][g]['map_SHA256'] for v in measured.values())
        d=delta(measured['front'],measured['base'])
        original=delta(measured['front'],read(ROOT/'analysis/first539-verification.json')['phases'][i-1]['row'])
        phases.append(dict(phase=i,**measured,delta=d,versus_MMC540=original,
                           gate=all(v['last_ACK_ms']<0 and v['dense_VB']<0 and v['dense_ms']<0 and not v['later_BG_windows']
                                    for v in (d,original)) and not any(measured['front']['waits'].values())))
        if a.after_tile_arm:
            td=delta(measured['tail'],measured['base'])
            to=delta(measured['tail'],read(ROOT/'analysis/first539-verification.json')['phases'][i-1]['row'])
            phases[-1].update(tail_delta=td,tail_versus_MMC540=to,tail_gate=all(v['last_ACK_ms']<0 and v['dense_VB']<0 and v['dense_ms']<0
                              and not v['later_BG_windows'] for v in (td,to)) and not any(measured['tail']['waits'].values()))
    tests={n:read(a.checks/f'{n}{run}.json') for n,run in [('guards','07'),('windows','02'),('menu','02')]}
    digest=sha(a.arm/'obj-nes-100/firmware.stm')
    assert tests['guards']['firmware']==tests['menu']['firmware']==tests['windows']['firmware_SHA256']==digest
    assert len(tests['guards']['rows'])==14 and tests['windows']['layout']=='trimmed'
    assert [r['displays'] for r in tests['windows']['accepted']]==[2,2]
    assert all(r['released']==int(k=='normal') for k,r in tests['menu']['rows'].items())
    tail_tests=None
    if a.after_tile_arm:
        tail_tests={n:read(a.checks/f'{n}{run}.json') for n,run in [('guards','06'),('windows','03'),('menu','03')]}
        assert tail_tests['guards']['firmware']==tail_tests['menu']['firmware']==tail_tests['windows']['firmware_SHA256']==sha(a.after_tile_arm/'obj-nes-100/firmware.stm')
        assert len(tail_tests['guards']['rows'])==16 and tail_tests['windows']['layout']=='trimmed'
        assert [r['displays'] for r in tail_tests['windows']['accepted']]==[2,2]
        assert all(r['released']==int(k=='normal') for k,r in tail_tests['menu']['rows'].items())
    board=read(ROOT/'analysis/trial540-verification.json')
    costs={k:{n:t['windows'][n] for n in ('firmware_SHA256','firmware_B','Flash_free_B','BSS_B')}
           for k,t in [('front',tests),('tail',tail_tests)] if t}
    return dict(phases=phases,gate=all(p['tail_gate' if a.after_tile_arm else 'gate'] for p in phases),tests=tests,tail_tests=tail_tests,builds=costs,
                unchanged_board=dict(evidence='analysis/trial540-verification.json',SHA256=sha(ROOT/'analysis/trial540-verification.json'),
                                     cost=board['board'],SOF_SHA256=board['SOF_SHA256'],new_FIT=False),
                selected=False,hardware_package=False,
                scope='Actual linked ARM/shared SPI/SysTick/65816, 53 fixed captures and repeated 8-frame boot ROM grant calendar. Two starts and identical completion-counter control; not physical gameplay FPS.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','plans','calendar','base_arm','arm','client','checks','out'):p.add_argument('--'+n.replace('_','-'),type=Path,required=True)
    p.add_argument('--after-tile-arm',type=Path)
    p.add_argument('--decode',action='store_true')
    a=p.parse_args();r=analyze(a)
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(gate=r['gate'],phases=[dict(phase=p['phase'],front=p['delta'],tail=p.get('tail_delta')) for p in r['phases']])))
