# SPDX-License-Identifier: MIT
"""Compare the second BG plan through physical PPU writes in two closed schedules."""
import argparse
import json
from pathlib import Path

from analyze_nes_map617 import csv_groups, ms, one, read, sha, timing
from analyze_nes_oam618 import work
from test_nes_obj609 import lanes
from test_nes_service509_schedule import Calendar


def ppu(rows, folder):
    packets=read_lines(folder/'packets.jsonl')
    # Measure the 144B BG run itself even if a different descriptor grouping
    # splits it. Idle descriptors log at MDMAEN; sealed descriptors log at
    # the first write. The PPU trace supplies the corresponding last write.
    dmas=[]
    for r in csv_groups(folder/'tile532.csv').get(954,[]):
        if r['event']=='tile':
            i=next(i for i,e in enumerate(rows) if e['clock']==r['clock'] and e['event']=='idle524')
            dmas.append((r['dst'],r['n'],rows[i+1],rows[i+2]))
    for r in csv_groups(folder/'seal528.csv')[954]:
        if r['event']=='dma' and r['port']==24:
            i=next(i for i,e in enumerate(rows) if e['clock']==r['clock'] and e['event']=='ppu_dma')
            dmas.append((r['dst'],r['bytes'],rows[i],rows[i+1]))
    required=set(range(1968,1968+144))
    done=set();writes=[]
    for dst,n,start,end in dmas:
        touched=required.intersection(range(dst-0xc000,dst-0xc000+n))
        if not touched:continue
        assert start['event']=='ppu_dma' and end['event']=='ppu_last' and start['value']==n
        assert not done.intersection(touched)
        done.update(touched)
        writes.append(dict(B=len(touched),first=start['clock'],last=end['clock'],frame=end['frame'],line=end['line']))
    accepted=set();acks=[]
    for row in rows:
        if row['event']!='ack' or (row['op'],row['section'])!=(7,0):continue
        _,push,header,data=packets[row['index']-1]
        h=bytes.fromhex(header);off=int.from_bytes(h[10:12],'little')
        touched=required.intersection(range(off,off+len(bytes.fromhex(data))))
        if touched:
            assert not accepted.intersection(touched)
            accepted.update(touched);acks.append(dict(B=len(touched),push=push,accepted=row['clock']))
    assert done==accepted==required
    assert max(a['accepted'] for a in acks)<min(w['first'] for w in writes)
    return acks,writes


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def measure(d,cal,addresses):
    t=timing(d);w=t['watched']
    cpu=csv_groups(d/'window.csv');rows=cpu[954];p=read(d/'obj-phases.json')['954']
    last=one([v for v in cpu[953] if v['op']==3],'reveal')
    acks,writes=ppu(rows,d)
    bg=[r for r in p['cache611'] if r[0]==0]
    assert [r[1] for r in bg]==addresses and len(bg)==160
    reads=bg[48:144]
    j=read(d/'joint.json')
    assert j['parameters']['ROM_calendar']==cal.summary and j['parameters']['ROM_phase']==0
    for _,addr,req,grant,resp,mode in reads:
        assert mode=='ROM' and cal.select(req+1)==(grant,resp)
    first_window=bg[0][3]*8//cal.period
    spi=[e for e in read(d/'events.json') if e['generation']==954 and e['event']=='SPI']
    events=[e for e in spi if e['opcode']=='0xe9']
    banks=p['banks557'];assert len(banks)==len(events)
    assert all(abs(b['seal']-e['clock'])<1 for b,e in zip(banks,events))
    early={v for x in w[955]['early'] for v in range(x['offset'],x['offset']+x['B'],64)}
    seal=[x for x in rows if x['op']==3]
    final=one(seal,'final212')
    last_seal=[row for row in cpu[957] if row['op']==3]
    terminal={event:{k:row[k] for k in ('frame','line','clock')}
              for event in ('load','final212','reveal','ack') for row in [one(last_seal,event)]}
    last_beam=[r['line'] for r in csv_groups(d/'seal528.csv')[954] if r['event']=='latch' and r['clock']>=final['clock']]
    tile_e1,=[e for e in spi if e['opcode']=='0xe1' and e['packet_opcode']==7 and abs(e['clock']-acks[-1]['push'])<=1]
    stamps=dict(E9_start=events[1]['start'],E9=banks[1]['seal'],first_request=reads[0][2],ROM96_end=reads[-1][4],
                BG144_ready=next(v['ready'] for v in p['boundaries561'] if v['prior_B']==144),
                E1_start=tile_e1['start'],E1_push=acks[-1]['push'],accepted=acks[-1]['accepted'],DMA_end=writes[-1]['last'],
                SEAL=one(seal,'load')['clock'],display=one(seal,'reveal')['clock'],ACK=one(seal,'ack')['clock'])
    return dict(stamps=stamps,from_display953_ms={k:ms(v-last['clock']) for k,v in stamps.items()},
                previous_display=last['clock'],first_ROM_window=first_window,
                ROM96_in_first_window=sum(r[4]*8//cal.period==first_window for r in reads),
                ROM96_first_grant=reads[0][3],bank_counts=[b['count'] for b in banks],
                e9_B=sum(e['bytes'] for e in events),wire_B=j['wire_B'],SysTick_calls=j['SysTick_calls'],
                after_SEAL_DMA_B=w[954]['after_SEAL_DMA_B'],early_map_B_954=sum(x['B'] for x in w[954]['early']),
                final_beam_samples_954=last_beam,final_wait_954=w[954]['final_waits'],
                max_bulk_banks=j['max_bulk_banks'],acks=acks,writes=writes,
                BG144_DMA_before_SEAL=writes[-1]['last']<stamps['SEAL'],
                final_wait_957=w[957]['final_waits'],terminal_957=terminal,first_map_955_B=w[955]['first_window_DMA_B'],
                last_map_955_B=64*len(early.intersection(range(3200,3584,64))),dense_mean_ms=t['dense_ms'],
                dense_VB=t['dense_VB'],intervals={g:w[g]['display_VB'] for g in w},last_ACK=t['last_ACK'],
                capture_margin_ms=t['min_capture_reuse_ms'],all_VB=t['all_display_VB'],VRAM_DMA_B=j['vram_DMA_B'],
                client=j['client_SHA256'],arm=j['firmware_SHA256'],
                pins={f:sha(d/f) for f in ('joint.json','events.json','window.csv','seal528.csv','tile532.csv','obj-phases.json','packets.jsonl')})


def compare(a):
    cal=Calendar(a.calendar); phases=[]
    plans=read(a.plans/'frame954/plans.json')
    addresses=[addr for _,h in plans for q in [bytes.fromhex(h)] if q[6]==0 for _,addr in lanes(q)]
    prior=read(a.reference)
    modes=['arm01','arm02','arm04','arm06']
    for phase in (1,2):
        base=a.traces/f'nes-tile619-coverage{phase}'
        ref=read(base/'joint.json');ctrl=measure(base,cal,addresses);original=work(base)
        assert all(ctrl['pins'][k]==v for k,v in prior['phases'][phase-1]['coverage']['pins'].items())
        data=dict(control=ctrl)
        for mode in modes:
            d=a.traces/f'nes-bg620-{mode}-{phase}';j=read(d/'joint.json')
            assert all(j[k]==ref[k] for k in ('parameters','ROM_read_allocations','client_SHA256','vram_DMA_B'))
            assert j['firmware_SHA256']==sha(a.build/mode/'src/obj-nes-100/firmware.stm')
            assert work(d)==original and all(sha(base/n)==sha(d/n) for g in range(905,958)
                                             for n in (f'frame-{g}.rgb',f'map-{g}.bin'))
            r=measure(d,cal,addresses)
            r['changed_VB']={g:n-ctrl['all_VB'][g] for g,n in r.pop('all_VB').items() if n!=ctrl['all_VB'][g]}
            r['last_ACK_delta_ms']=ms(r['last_ACK']-ctrl['last_ACK'])
            r['display953_delta_ms']=ms(r['previous_display']-ctrl['previous_display'])
            r['delta_from_display953_ms']={k:v-ctrl['from_display953_ms'][k] for k,v in r['from_display953_ms'].items()}
            r['pass']=bool(r['ROM96_in_first_window']==96 and r['intervals'][954]==4 and r['intervals'][952]==4
                           and r['delta_from_display953_ms']['accepted']<0 and r['delta_from_display953_ms']['DMA_end']<0
                           and r['last_ACK_delta_ms']<0 and r['first_map_955_B']>=192 and r['last_map_955_B']==384
                           and r['final_wait_957']==0)
            data[mode]=r
        del ctrl['all_VB'];phases.append(data)
    guards={}
    for m in modes:
        arm=read(a.build/f'seeded{m[-2:]}.json')
        assert arm['arm']==sha(a.build/m/'src/obj-nes-100/firmware.stm')
        priority=read(a.traces/f'nes-bg620-{m}-test_nes_map616_edges/edges.json')
        stop=read(a.traces/f'nes-bg620-{m}-test_nes_seal538_stop/result.json')
        assert {(r['generation'],r['fault']) for r in priority if 'fault' in r}=={
            (g,f) for g in (906,907) for f in ('missing','duplicate')}
        assert {r['case'] for r in priority if r['grant']==0}>={'head','both','stop'}
        assert {(r['generation'],r['boundary'],r['status']) for r in stop}=={
            (g,k,0xe4) for g in (906,907) for k in ('budget538','final212')}
        guards[m]=dict(ARM=arm,priority=priority,STOP=stop)
    codec=read(a.build/'codec02/result.json')
    assert all(codec['candidate']==sha(a.build/m/'src/nes_plan_wire199.h') for m in ('arm04','arm06'))
    result=dict(phases=phases,passes={m:all(p[m]['pass'] for p in phases) for m in modes},codec=codec,
                Flash_B={m:(a.build/m/'src/obj-nes-100/firmware.stm').stat().st_size for m in modes},guards=guards)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','calendar','plans','reference','build','out'):p.add_argument('--'+k,type=Path,required=True)
    compare(p.parse_args())
