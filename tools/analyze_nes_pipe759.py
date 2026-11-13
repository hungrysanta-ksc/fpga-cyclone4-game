# SPDX-License-Identifier: MIT
"""Tie immutable range production to actual E1 DMA and checked SNES head service."""
import argparse
import json
from pathlib import Path
from analyze_nes_bg750 import counters
from analyze_nes_map628 import normalize
from analyze_nes_owner739 import csv_groups,ms,read,sha
from analyze_nes_rows757 import ranges
from analyze_nes_window756 import summarize

def inspect(folder,metric):
    events=[e for e in read(folder/'events.json') if e['generation']==957]
    e1=[e for e in events if e.get('opcode')=='0xe1']
    cpu=csv_groups(folder/'window.csv')[957]
    loads=[e for e in cpu if e['event']=='load']
    acks=[e for e in cpu if e['event']=='ack']
    assert len(loads)==len(acks)==len(e1)
    head=[(a['clock'],b['clock']) for a,b in zip(loads,acks,strict=True)]
    deadline=metric['first248'][1]
    stamp=lambda t:ms(t-deadline)
    material=ranges(folder,metric)['rows']
    details={}
    for off in (2048,3008):
        writes=[e for e in events if e['event']=='map_store757' and off<=e['offset']<off+192]
        def per_byte(e):
            t=e['clock'];in_spi=any(p.get('DMA_start759',float('inf'))<=t<=p.get('DMA_end759',-1) for p in e1)
            in_head=any(a<=t<=b for a,b in head)
            return in_spi,in_head
        if not writes:raise AssertionError(off)
        counts=[per_byte(e) for e in writes]
        m=material[off]
        details[off]=dict(first_write=stamp(writes[0]['clock']),last_write=m['last_write'],
            final_slot=m['last_required_slot'],map_E1=m['first_E1'],map_return=m['CPU_return'],
            bytes_written=sum(len(bytes.fromhex(e['new'])) for e in writes),
            during_E1_B=sum(len(bytes.fromhex(e['new'])) for e,(spi,snes) in zip(writes,counts) if spi),
            during_65816_B=sum(len(bytes.fromhex(e['new'])) for e,(spi,snes) in zip(writes,counts) if snes),
            during_both_B=sum(len(bytes.fromhex(e['new'])) for e,(spi,snes) in zip(writes,counts) if spi and snes))
    return details

def analyze(temp,probe):
    data=dict(phases={},selected='753')
    for n in (1,2):
        base=temp/f'nes-credit753-prefix{n}'
        work=normalize(base)[0]
        rows=data['phases'][n]={}
        for key in ('753','serial','pipe','join','split','ordered'):
            if key=='753':
                d=temp/f'nes-pipe759-control{n}'
                if not (d/'joint.json').is_file():d=temp/f'nes-tail758-control{n}'
            else:d=temp/f'nes-pipe759-{key}{n}'
            v=summarize(d,base,n,work,ordered_page=False)
            arm=probe.parent/'nes-credit753/arm-prefix' if key=='753' else probe/('arm-pipe' if key=='join' else 'arm-'+key)
            fw=arm/'src/obj-nes-100/firmware.stm'
            assert v['firmware']==sha(fw)
            client=probe/'client-join' if key in ('join','split') else probe.parent/'nes-static751/sharedfast'
            assert v['ROM']==sha(client/'sink165.sfc')
            v.update(Flash_B=fw.stat().st_size,BSS_B=int((arm/'size.log').read_text().splitlines()[-1].split()[2]),
                  ROM_free_B=read(client/'build.json')['physical_free_B'],ranges759=inspect(d,v))
            ev=[e for e in read(d/'events.json') if e['generation']==957]
            bound=v['first248'][1]
            v['BG_end_to_OBJ_done_ms']=ms(next(e['clock'] for e in ev if e['event']=='prepare_enter')-
                                         next(e['clock'] for e in ev if e['event']=='bg_map_frozen'))
            dma=counters(d/'dma748.csv')
            v['actual_page_DMA_B']={
                g:[r['bytes'] for r in dma if r['g']==g and start<=r['source']<start+1536]
                for g,start in ((952,0xd800),(957,0x5800))}
            for offset,window in v['ranges759'].items():
                packet=next(r for r in v['page'] if r['offset']==offset)
                assert window['bytes_written']==114 and window['last_write']<=ms(packet['start']-bound)

            # Keep the chronology of what interrupted adjacent map descriptors.
            page_wire=[(e['op'],e['section'],e['offset']) for e in ev if e['event']=='wire664']
            v['map_output_order']=page_wire
            v['first_output_ms']=ms(next(e['clock'] for e in ev if e['event']=='output_enter531')-bound)
            v['page_E1_start_ms']=[ms(r['start']-bound) for r in v['page']]
            v['pre_BG_E1']=[r['offset'] for r in v['page'] if r['start']<next(e['clock'] for e in ev if e['event']=='bg_map_frozen')]
            if key=='753':
                start=next(e['clock'] for e in ev if e['event']=='planner_enter')
                required=[e for e in ev if e['event']=='SPI' and e['opcode'] in ('0xe1','0xe9') and
                          start<=e['start'] and e['clock']<=v['page'][-1]['push']+1]
                count=sum(e['bytes'] for e in required)
                wire=count*8/2625
                charged=sum(ms(e['clock']-e['start']) for e in required)
                last_service=ms(v['page'][-1]['retired']-v['page'][-1]['accepted'])
                available=ms(bound-start)
                v['same_prefix_budget']=dict(bytes=count,transactions=len(required),available_ms=available,
                        wire_ms=wire,with_driver_ms=charged,last_service_ms=last_service,
                        minimum_wire_short_ms=wire-available,
                        driver_plus_last_service_short_ms=charged+last_service-available)
            rows[key]=v
            v['dense_delta_ms']=v['mean_ms']-rows['753']['mean_ms']
            v['ACK_delta_ms']=ms(v['ACK']-rows['753']['ACK'])
            v['qualified']=v['safe_schedule'] and v['intervals'][957]==2 and v['last_map_late_ms']<=0 and v['Flash_B']<=212992 and v['dense_delta_ms']<0 and v['ACK_delta_ms']<0
    for phase,offset in ((1,2048),(2,3008)):
        rows=data['phases'][phase]
        assert rows['serial']['ranges759'][offset]['during_E1_B']==0
        assert rows['pipe']['ranges759'][offset]['during_E1_B']==114
    assert data['phases'][2]['split']['ranges759'][3008]['during_65816_B']>0
    data['eligible']=[k for k in ('serial','pipe','join','split','ordered') if all(r[k]['qualified'] for r in data['phases'].values())]
    if data['eligible']:data['selected']=data['eligible'][0]
    data['guards']={k:read(probe/f'guards-{k}.json') for k in ('serial','pipe','split','ordered')}
    for k,g in data['guards'].items():assert g['firmware']==g['menu']['firmware']==data['phases'][1][k]['firmware']
    data['driver']=read(probe/'dma01/result.json')
    assert data['driver']['firmware']==data['phases'][1]['pipe']['firmware']
    data['split_driver']=read(probe/'dma-split/result.json')
    assert data['split_driver']['firmware']==data['phases'][1]['split']['firmware']
    data['boot']=read(temp/'nes-pipe759-boot/result.json')
    data['receiver']={}
    for n in (1,2):
        data['receiver'][n]={}
        for f in ('before','during','head','stale'):
            r=read(temp/f'nes-pipe759-join{n}-{f}/verified751.json')
            assert r['client']==data['phases'][n]['join']['ROM'] and r['commits']==(53 if f=='head' else 52)
            data['receiver'][n][f]=r
    # The 248 return deadline alone cannot guarantee the following OBJ slot.
    # Translate the actual baseline map->OBJ instruction/DMA distance back
    # from the end of line 256. No overhead for return->MDMAEN is assumed.
    data['latest_map_start_vs_end248_ms']={}
    for n,rows in data['phases'].items():
        ref=rows['753']
        gap=ref['OBJ']['clock']-ref['map_DMA'][957][0]['clock']
        data['latest_map_start_vs_end248_ms'][n]=ms(8*1364-gap)
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+'\n',encoding='utf8',newline='\n')
