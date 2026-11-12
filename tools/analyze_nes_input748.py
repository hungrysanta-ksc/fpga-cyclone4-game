# SPDX-License-Identifier: MIT
"""Reconcile full-link schedules with map retirements, D0 input and actual $420B writes."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_owner739 import csv_groups, ms, packets, read, sha
from analyze_nes_receipt742 import whole
from check_nes_game478 import crc


def decision(folder):
    with (folder/'decision748.csv').open() as f:
        return list(csv.DictReader(f))


def display(folder, dma_dir):
    rows=csv_groups(folder/'window.csv')
    ack=next(r['clock'] for r in rows[957] if r['op']==3 and r['event']=='ack')
    visible=[next(r['clock'] for r in rows[g] if r['op']==3 and r['event']=='reveal') for g in (951,957)]
    seal=next(r['clock'] for r in rows[957] if r['op']==3 and r['event']=='load')
    with (dma_dir/'dma748.csv').open() as f:
        all_dma=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
    obj=[r for r in all_dma if r['g']==957 and r['source']==19104]
    assert sum(r['bytes'] for r in obj)==288
    maps={}
    for g in (952,957):
        before=next(r['clock'] for r in rows[g] if r['op']==3 and r['event']=='load')
        maps[g]=[d for d in all_dma if d['g']==g and d['clock']<before and d['bytes']==1536 and d['source']==(55296 if g==952 else 22528)]
    assert all(len(v)==1 for v in maps.values())
    map_end=next(r for r in rows[957] if r['clock']>maps[957][0]['clock'] and r['event']=='ppu_last')
    mark=maps[957][0]
    vblank=mark['clock']-(mark['line']-225)*1364-mark['h']
    before_deadline=any(vblank<=d['clock']<vblank+33*1364 and d['clock']<seal for d in obj)
    return dict(preceding_VBlank_257=before_deadline,long_map_end=map_end,OBJ=obj,OBJ_before_SEAL=bool(obj[0]['clock']<seal),seal=seal,map_DMA=maps,visible=visible,
                dense_ms=ms(visible[1]-visible[0])/6,last_ACK=ack)


def comparison(folder, base, ref, dma_dir):
    detail=whole(folder,base)
    cpu=display(folder,dma_dir)
    assert cpu['last_ACK']==detail['final_ACK'] and abs(detail['dense_ms']-cpu['dense_ms'])<1e-8
    maps=[]
    first_difference=None
    heads=packets(folder)
    baseline=packets(base)
    for g in range(905,958):
        def group(p):
            return [(h[:2]+h[4:],b,t) for h,b,t in p[g] if h[1]==2]
        if first_difference is None:
            for (h,_,t),(old,_,old_t) in zip(heads[g],baseline[g]):
                if t!=old_t or h!=old:
                    first_difference=dict(g=g,op=h[0],section=h[1],tick=t,delta=t-old_t)
                    break
        now,before=group(heads),group(baseline)
        assert [(h,b) for h,b,_ in now]==[(h,b) for h,b,_ in before]
        maps.extend((g,i,x[2]-y[2]) for i,(x,y) in enumerate(zip(now,before)))
    changed=[x for x in maps if x[2]]
    assert len(maps)==521
    events=[e for e in read(folder/'events.json') if e.get('generation')==957]
    oam=next(h for h,_,t in heads[957] if t==detail['OAM_push'])
    samples=[e for e in events if e.get('event')=='idle676_enter' and detail['map_last_ACK']<e['clock']<detail['scroll_push']]
    assert all(e['sent']==e['retired'] for e in samples)
    spi=[e for e in events if e.get('event')=='SPI']
    repayment=[]
    for e in samples:
        if detail['OAM_push']<e['clock']:
            s=max((s for s in spi if s['clock']<e['clock']),key=lambda s:s['clock'])
            raw=bytes.fromhex(s['reply'])
            assert s['opcode']=='0xe0' and raw[1]==0xf7 and raw[3:5]==raw[5:7]
            assert raw[7:19]==bytes((0,9))+oam[2:10]+bytes((0x65,0x9a)) and raw[19]==crc(raw[1:19],8,7,0)
            repayment.append(dict(reply=raw.hex(),E0_end=s['clock'],input=e['clock']))
    assert (folder/'startup-clock.txt').read_bytes()==(base/'startup-clock.txt').read_bytes()
    poll=read(folder/'result.json')['first_packet_poll_masterclock']
    assert poll==read(base/'result.json')['first_packet_poll_masterclock']
    return dict(**cpu,first_SNES_poll=poll,first_map=next(t for h,_,t in heads[905] if h[1]==2),
                first_packet_difference=first_difference,map_count=len(maps),changed_maps=len(changed),first_changed_map=changed[:1],
                map957_delta=[d for g,_,d in maps if g==957],
                OBJ_offer=detail['OBJ_push'],OBJ_load=detail['OBJ_load'],OBJ_receipt=detail['OBJ_ACK'],
                OAM_offer=detail['OAM_push'],OAM_receipt=detail['OAM_ACK'],last_map_ACK=detail['map_last_ACK'],
                input_before_OBJ=sum(e['clock']<detail['OBJ_push'] for e in samples),repayment=repayment,
                after_map_input_window=[dict(op=s['opcode'],start=s['start'],end=s['clock']) for s in spi
                       if detail['map_last_ACK']<s['start']<detail['scroll_push']],
                dense_delta_us=1000*(cpu['dense_ms']-ref['dense_ms']),ACK_delta=cpu['last_ACK']-ref['last_ACK'],
                intervals=detail['intervals'],final_wait957=detail['final_wait957'],public951=detail['public951'],
                ROM_reads=detail['ROM_reads'],wire_B=detail['wire_B'],pins=detail['pins'],ARM=detail['firmware'])


def analyze(a):
    result=dict(stage=748,retained=727,phases={},ARM={})
    for k in ('linked','normal','control'):
        d=a.probe/k
        fw=d/'src/obj-nes-100/firmware.stm'
        result['ARM'][k]=dict(bytes=fw.stat().st_size,free=212992-fw.stat().st_size,sha256=sha(fw),
                             size=(d/'size.log').read_text().splitlines()[-1].split()[:3])
        if k!='control':
            for guard in ('input748','deadline719','menu533'):
                f=a.probe/f'{k}-{guard}.json'
                data=read(f)
                assert data['firmware']==sha(fw)
                result['ARM'][k][guard]=data
    client=a.client
    info=read(client/'build.json')
    result['ROM']={k:info[k] for k in ('body_SHA256','prefix_B','physical_ROM_B','physical_free_B','small_tile_B')}
    for n in (1,2):
        base=a.temp/f'nes-pair727-a{n}'
        observer=a.temp/f'nes-input748-ref{n}-decision'
        ref=display(base,observer)
        v=result['phases'][n]={}
        for k in ('ref','control','linked'):
            folder=base if k=='ref' else a.temp/f'nes-input748-{k}{n}'
            tap=observer if k=='ref' else folder
            r=v[k]=comparison(folder,base,ref,tap)
            assert all(bool(r['map_DMA'][g]) for g in (952,957))
            if k=='linked':
                assert len(r['repayment'])==1
                assert not r['preceding_VBlank_257'] and r['final_wait957']==0
            if k!='ref':assert r['ARM']==result['ARM'][k]['sha256']
            if k!='control':
                replay=a.temp/f'nes-input748-{k}{n}-decision'
                assert read(replay/'audit.json')['actual_events']==read(replay/'audit.json')['reference_events']
                r['decisions']=decision(replay)
        single=a.temp/f'nes-input748-ref{n}-single'
        v['single']=dict(**display(single,single),**read(single/'one_input.json'),decisions=decision(single))
        folder=a.temp/f'nes-input748-linked{n}'
        v['faults']={}
        for fault in ('stop','stale','head'):
            d=a.temp/f'nes-input748-linked{n}-{fault}'
            out=read(d/'result.json')
            assert out['passed'] and out['commits']==(53 if fault=='head' else 52)
            v['faults'][fault]=dict(commits=out['commits'],status=out['last_status'],trace=sha(d/'window.csv'))
            if fault=='head':
                tick,index,op,section=map(int,(d/'head748.txt').read_text().split())
                e=next(r for r in csv_groups(d/'window.csv')[957] if r['clock']>tick and r['event'] in ('load','ppu_dma'))
                assert e['event']=='load' and (e['index'],e['op'],e['section'])==(index,op,section)
                v['faults'][fault]['head']=e
            else:assert sha(d/'retained.rgb')==sha(folder/'frame-956.rgb')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','probe','client','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
