# SPDX-License-Identifier: MIT
"""Check the retained WRAM, exact consumer clock comparisons, faults and restoration."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from replay_nes_delta738 import SIZE, compact

HZ = 21477272


def ms(ticks):
    return round(1000*ticks/HZ, 6)


def table(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(root):
    rows=table(root/'window.csv')
    def select(g,event):
        return [r for r in rows if int(r['g'])==g and r['event']==event]
    def one(g,event):
        r,=select(g,event)
        return r
    def time(g,event):
        return int(one(g,event)['clock'])
    def service(g):
        times=Counter()
        for r in rows:
            if int(r['g'])==g and r['section']=='5' and r['event'] in ('load','ack'):
                times[r['index']]+=int(r['clock'])*(1 if r['event']=='ack' else -1)
        assert times and min(times.values())>0
        return ms(sum(times.values()))
    def last(g,op,event):
        return next(r for r in reversed(select(g,event)) if r['op']==op)
    def map_start(g):
        r,=[r for r in select(g,'ppu_dma') if r['value']=='1536']
        return int(r['clock'])
    final=last(957,'3','ack')
    return dict(mean952_957_ms=ms((time(957,'reveal')-time(951,'reveal'))/6),
        interval957_ms=ms(time(957,'reveal')-time(956,'reveal')),
        interval957_VBlank=int(one(957,'reveal')['frame'])-int(one(956,'reveal')['frame']),
        last_ACK_clock=int(final['clock']),seal_clock=int(last(957,'3','load')['clock']),
        OBJ_load_line=int(last(957,'7','load')['line']),OAM_load_line=int(last(957,'9','load')['line']),
        cold905_service_ms=service(905),section957_service_ms=service(957),
        map1536_start={str(g):map_start(g) for g in (952,957)},
        frames=json.loads((root/'result.json').read_text())['commits'],
        window_sha256=digest(root/'window.csv'), commits_audited=json.loads((root/'audit.json').read_text())['frames'])


def measure(temp):
    result=dict(stage=738,phases={},faults={},restores={},menu={})
    for phase in (1,2):
        ref=temp/f'nes-wram738-ref{phase}'
        inputs=temp/f'nes-pair727-a{phase}'
        writes=table(ref/'writes738.csv')
        cut=next(i for i,r in enumerate(writes) if r['event']=='before957')
        base=int(writes[0]['address'])
        assert SIZE==int(writes[0]['count'])
        dma=[r for r in writes[1:cut] if r['event']=='DMA_to_WRAM']
        assert all(int(r['address'])+int(r['count'])<=base or int(r['address'])>=base+SIZE for r in dma)
        assert not any(r['event'] in ('port','direct') for r in writes[:cut])
        old=(ref/'ack955.bin').read_bytes()
        assert old==compact(inputs/'expected-955.bin')
        assert all((ref/(s+'.bin')).read_bytes()==old for s in ('ack956','begin957','before957'))
        new=(ref/'ack957.bin').read_bytes()
        assert new==compact(inputs/'expected-957.bin')
        for k in ('direct','port'):
            assert sorted(int(r['address']) for r in writes[cut:] if r['event']==k)==list(range(base,base+SIZE))
        baseline=metrics(ref)
        outputs={}
        for name in ('warm','floor'):
            root=temp/f'nes-delta738-{name}{phase}'
            cand=metrics(root)
            assert cand['map1536_start']==baseline['map1536_start']
            assert (root/'ack957.bin').read_bytes()==new
            cand.update(delta_mean_ms=round(cand['mean952_957_ms']-baseline['mean952_957_ms'],6),
                        delta_last_ACK_ms=ms(cand['last_ACK_clock']-baseline['last_ACK_clock']),
                        delta_SEAL_ms=ms(cand['seal_clock']-baseline['seal_clock']))
            outputs[name]=cand
        result['phases'][phase]=dict(base=baseline,tests=outputs,bank_base=base,
            other_WRAM_DMA_before_reuse=len(dma),target_writes_before_reuse=0,
            pre_reuse_DMA=[[int(r[k]) for k in ('g','clock','address','count')] for r in dma],
            controls_after_reuse=dict(Counter(r['event'] for r in writes[cut:])),
            writes_sha256=digest(ref/'writes738.csv'),before_sha256=digest(ref/'ack955.bin'),
            after_sha256=digest(ref/'ack957.bin'),matched_events=json.loads((ref/'audit.json').read_text())['matched_events'],
            changes=[[i,x,y] for i,(x,y) in enumerate(zip(old,new)) if x!=y],
            wire=json.loads((temp/f'nes-delta738-warm{phase}'/'wire.json').read_text()))
    ref=temp/'nes-wram738-ref1'
    for mode in ('stale','corrupt','partial','stop'):
        path=temp/f'nes-delta738-{mode}'
        raw=json.loads((path/'result.json').read_text())
        assert raw['passed'] and raw['commits']==52 and raw['last_status']==(228 if mode=='stop' else 224)
        assert digest(path/'retained.rgb')==digest(ref/'frame-956.rgb')
        result['faults'][mode]=dict(status=raw['last_status'],commits=52,
            residual_sha256=digest(path/'rejected957.bin'),retained_956_RGB=digest(path/'retained.rgb'))
    for mode,tag in (('poison','restore'),('partial','recover-partial'),('stop','recover-stop2')):
        path=temp/f'nes-delta738-{tag}'
        if mode=='poison':
            assert (path/'before957.bin').read_bytes()==bytes([0xa5])*SIZE
        else:
            assert digest(path/'before957.bin')==result['faults'][mode]['residual_sha256']
        assert digest(path/'ack957.bin')==digest(ref/'ack957.bin')
        assert digest(path/'frame-957.rgb')==digest(ref/'frame-957.rgb')
        result['restores'][mode]=metrics(path)
    for trial in ('690','704'):
        path=temp/f'nes-wram738-menu{trial}.json';j=json.loads(path.read_text())
        assert j['rows']['normal']['released']==1 and j['marker_cases']==4
        result['menu'][trial]=dict(firmware=j['firmware'],modes=list(j['rows']),evidence=digest(path))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--temp',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(measure(a.temp),indent=2)+'\n',encoding='utf8')
