# SPDX-License-Identifier: MIT
"""Compare the 616B baseline, 617, OAM-only and checked SEAL prefixes at equal work."""
import argparse
import json
from pathlib import Path

from analyze_nes_map617 import ROOT, contents, csv_groups, consumed_tiles, ms, one, read, sha, timing


def work(folder):
    ordinary,raw=contents(folder)
    return ({k:v for k,v in ordinary.items() if k[0][0]!=7},raw,consumed_tiles(folder))


def metrics(folder):
    r=timing(folder)
    j=read(folder/'joint.json')
    w=r['watched']
    rows=csv_groups(folder/'window.csv')
    e=read(folder/'events.json')
    s=[x for x in rows[954] if x['op']==3]
    validation=one(s,'upload165_entry')
    fresh=next((x['clock'] for x in s if x['event'] in ('wait169','final212')),None)
    assert fresh is not None
    ends=[x for x in s if x['event']=='ppu_last']
    dmas=[]
    for x in s:
        if x['event']=='ppu_dma' and x['clock']<fresh:
            end=next(y for y in ends if y['clock']>=x['clock'])
            assert x['frame']==end['frame']==validation['frame'] and x['value']<=384
            assert 225<=x['line']<=end['line']<=261
            dmas.append(dict(B=x['value'],first=x['line'],last=end['line']))
    begin=one([r for r in rows[955] if r['op']==1],'ack')['clock']
    # Match the first OAM head by its exact packet PUSH.
    packets=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    head=next(x for x in rows[955] if x['section']==4 and x['event']=='load')
    push=packets[head['index']-1][1]
    send,=[r for r in e if r['generation']==955 and r['event']=='SPI' and r['opcode']=='0xe1' and abs(push-r['clock'])<=1]
    palette=[r for r in rows[955] if r['section']==3 and r['event']=='load']
    palette_push=packets[palette[-1]['index']-1][1]
    map_end=None
    for i,x in enumerate(rows[955][:-2]):
        y,z=rows[955][i+1:i+3]
        if x['event']=='idle524' and x['value']==65536+2048 and y['event']=='ppu_dma' and y['value']==1152:
            assert z['event']=='ppu_last'
            map_end=z['clock']
    grants=w[955]['early']
    units={p for x in grants for p in range(x['offset'],x['offset']+x['B'],64)}
    accepted={p for x in w[955]['map'] for p in range(x['offset'],x['offset']+x['B'],64)}
    assert set(range(2048,2048+19*64,64))<=accepted
    seal_trace=csv_groups(folder/'seal528.csv')[954]
    final=one(s,'final212')
    return dict(dense_ms=r['dense_ms'],dense_VB=r['dense_VB'],last_ACK=r['last_ACK'],
                display_952=w[952]['display_VB'],waits_957=w[957]['final_waits'],
                display_954=w[954]['display_VB'],display_955=w[955]['display_VB'],
                before_fresh_954=dmas,upload_wait_954_ms=w[954]['upload_wait_ms'],
                upload_entry_954_line=validation['line'],final_credit_954=one(seal_trace,'final_credit')['bytes'],
                waits_954=w[954]['final_waits'],wait_entry_954_lines=w[954]['wait_lines'],SEAL_head_954_line=w[954]['SEAL_head_line'],
                final_entry_954_line=final['line'],
                OAM_955_ms=dict(start=ms(send['start']-begin),push=ms(push-begin),head=ms(head['clock']-begin)),
                palette_push_to_OAM_start_ms=ms(send['start']-palette_push),
                end_1152_to_OAM_push_ms=ms(push-map_end) if map_end is not None else None,
                map_955_early=grants,last_384_B=64*len(units.intersection(range(3200,3584,64))),
                first_window_955_B=w[955]['first_window_DMA_B'],min_capture_reuse_ms=r['min_capture_reuse_ms'],
                all_display_VB=r['all_display_VB'],warm_DMA_checked=r['warm_DMA_checked'],cache=r['cache'],
                firmware=j['firmware_SHA256'],client=j['client_SHA256'],
                pins={n:sha(folder/n) for n in ('joint.json','window.csv','seal528.csv','packets.jsonl','obj-phases.json','events.json')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','arm','paced','arm-guards','client','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    previous=read(ROOT/'analysis/map617-verification.json')
    base_pins=read(ROOT/'analysis/map616-beam-verification.json')
    phases=[]
    for i in (1,2):
        paths=[a.traces/(f+str(i)) for f in ('nes-map616-beam','nes-map617-run','nes-oam618-arm','nes-oam618-checked','nes-oam618-paced')]
        for d,pins in zip(paths,(base_pins['phases'][i-1]['pins'],previous['phases'][i-1]['pins'])):
            assert all(sha(d/n)==digest for n,digest in pins.items())
        ref=read(paths[0]/'joint.json')
        baseline=work(paths[0])
        results=[]
        for d in paths:
            j=read(d/'joint.json')
            assert all(j[k]==ref[k] for k in ('parameters','ROM_read_allocations','vram_DMA_B'))
            assert work(d)==baseline
            for g in range(905,958):
                for name in (f'map-{g}.bin',f'frame-{g}.rgb'):
                    assert sha(paths[0]/name)==sha(d/name)
            assert not any((d/n).exists() for n in ('fault.json','map-error.txt','callback-error.txt'))
            results.append(metrics(d))
        b,rolling,oam,joint,paced=results
        assert b['client']==rolling['client']==oam['client']
        assert oam['firmware']==joint['firmware']==sha(a.arm/'obj-nes-100/firmware.stm')
        assert joint['client']==paced['client']==sha(a.client/'sink165.sfc')
        assert paced['firmware']==sha(a.paced/'obj-nes-100/firmware.stm')
        for r in (oam,joint,paced):
            r['delta_last_ACK_ms']=ms(r['last_ACK']-b['last_ACK'])
            r['both_times_improved']=r['dense_ms']<b['dense_ms'] and r['last_ACK']<b['last_ACK']
            r['requested_gate']=bool(r['last_384_B']==384 and r['first_window_955_B']>=192 and r['before_fresh_954']
                                     and r['display_952']==4 and r['waits_957']==0 and r['both_times_improved'])
            r['whole_blank_improved']=r['dense_VB']<b['dense_VB']
        isolated=read(a.traces/f'nes-oam618-fixedb{i}/audit.json')
        assert isolated['trace']==sha(a.traces/f'nes-oam618-fixedb{i}/window.csv')
        seal=read(a.traces/f'nes-oam618-seal{i}/audit.json')
        assert seal['trace']==sha(a.traces/f'nes-oam618-seal{i}/window.csv')
        phases.append(dict(base=b,rolling=rolling,oam=oam,joint=joint,paced=paced,fixed_OAM=isolated,fixed_SEAL=seal))
    guards=read(a.arm_guards)
    assert guards['ARM']==sha(a.paced/'obj-nes-100/firmware.stm')
    edges=read(a.traces/'nes-oam618-boundary02/edges.json')
    assert [(r['boundary'],r['B'],r['status']) for r in edges]==[
        ('checked-252',384,228),('checked-253',0,228),('checked-252-stop',0,228)]
    priority=read(a.traces/'nes-oam618-priority01/edges.json')
    assert {(r['generation'],r['fault']) for r in priority if 'fault' in r}=={
        (g,f) for g in (906,907) for f in ('missing','duplicate')}
    assert {r['case'] for r in priority if r['grant']==0}>={'head','both','stop'}
    stops=read(a.traces/'nes-oam618-stop01/result.json')
    assert {r['boundary'] for r in stops}=={'staged-3','staged-4','staged-5'}
    assert all((r['status'],r['commits'])==(228,49) for r in stops)
    result=dict(phases=phases,gate={k:all(p[k]['requested_gate'] for p in phases) for k in ('joint','paced')},
                flash_B={k:(s/'obj-nes-100/firmware.stm').stat().st_size for k,s in [('oam',a.arm),('paced',a.paced)]},arm_guards=guards,
                checked_edges=edges,priority=priority,staged_STOP=stops,client_build=read(a.client/'build.json'))
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
