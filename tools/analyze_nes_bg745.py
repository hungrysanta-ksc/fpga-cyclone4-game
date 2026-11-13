# SPDX-License-Identifier: MIT
"""Reconcile the live ARM issue stream with the two actual SNES DMA endpoints."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_nes_receipt742 import cpu_frame, whole
from analyze_nes_beam741 import records
from analyze_nes_owner739 import csv_groups, ms, packets, read, sha
from build_nes_bitmap743 import codec, optimal
from test_nes_arm745 import image


def timeline(folder, base):
    both = [packets(f) for f in (folder, base)]
    shifted = []
    count = 0
    tail = []
    for g in range(905,958):
        maps = [[(h[:2]+h[4:], b, t) for h,b,t in p[g] if h[1]==2] for p in both]
        assert [(h,b) for h,b,_ in maps[0]] == [(h,b) for h,b,_ in maps[1]]
        for i, ((_,_,now),(_,_,before)) in enumerate(zip(*maps)):
            count += 1
            if now!=before:shifted.append((g,i,now-before))
            if g==957:tail.append(now-before)
    r=whole(folder,base)
    first=read(folder/'result.json')['first_packet_poll_masterclock']
    assert first==read(base/'result.json')['first_packet_poll_masterclock']
    assert (folder/'startup-clock.txt').read_bytes()==(base/'startup-clock.txt').read_bytes()
    cpu=csv_groups(folder/'window.csv')[957]
    loads=[x for x in cpu if x['event']=='load']
    acks=[x for x in cpu if x['event']=='ack']
    frames=both[0][957]
    last_map=max(i for i,(h,b,t) in enumerate(frames) if h[1]==2)
    bg=next(i for i,(h,b,t) in enumerate(frames) if h[:2]==bytes((7,0)) and len(b)==48)
    obj=next(i for i,(h,b,t) in enumerate(frames) if h[:2]==bytes((7,1)) and len(b)==288)
    def edge(i):
        return dict(offer=frames[i][2],load=loads[i]['clock'],ack=acks[i]['clock'])
    bg_tap=next((x for x in records(folder/'tile532.csv') if x['g']==957 and x['src']==2112 and x['n']==48),None)
    if bg_tap:
        bgdma=next(x for x in r['prefix957'] if x['start']>=bg_tap['clock'])
    else:
        sealed=next(x for x in records(folder/'seal528.csv') if x['g']==957 and x['event']=='dma' and x['src']==2112)
        done=next(e for e in cpu if e['clock']>sealed['clock'] and e['event']=='ppu_last')
        bgdma=dict(start=sealed['clock'],end=done['clock'],size=sealed['bytes'],first_line=sealed['line'],
                   last_line=done['line'],after_SEAL=True)
    assert bgdma['size']==48
    longmap=next((x for x in r['prefix957'] if x['offset']==67584 and x['size']==1536),None)
    r['order957']=dict(BG=edge(bg),BG_DMA=bgdma,map=edge(last_map),OBJ=edge(obj),long_map=longmap)
    spi=[e for e in read(folder/'events.json') if e.get('event')=='SPI' and e['generation']==957 and
         frames[last_map][2]<e['clock']<=frames[obj][2]+1]
    r['map_to_OBJ_SPI']=[]
    for e in spi:
        sample=dict(op=e['opcode'],start=round(e['start']),end=round(e['clock']))
        if e['opcode']=='0xe0':
            data=bytes.fromhex(e['reply'])
            sample.update(sent=int.from_bytes(data[3:5],'big'),retired=int.from_bytes(data[5:7],'big'))
        r['map_to_OBJ_SPI'].append(sample)
    r['first_poll']=first
    r['map_issue']=dict(count=count,changed=len(shifted),first=shifted[:1],delta957=tail)
    if (folder/'dma745.csv').is_file():
        dma=[x for x in records(folder/'dma745.csv') if x['g']==957]
        if longmap:
            mark=next(x for x in dma if x['clock']==longmap['start'])
            assert mark['src']==22528 and mark['n']==1536
            r['order957']['queue_at_long_map']=mark
        prefix=[x for x in dma if x['src']==19104 and x['n']<288]
        for x in prefix:
            assert any(y['start']==x['clock'] and y['size']==x['n'] for y in r['prefix957'])
        r['OBJ_MDMAEN']=prefix
        r['margin_before_line258_clocks']=((258-prefix[0]['line'])*1364-prefix[0]['h'] if prefix else None)
    queued=r['order957'].get('queue_at_long_map',{})
    r['meets_exact']=bool(r['meets'] and not shifted and queued.get('nextsrc')==19104 and queued.get('nextbytes')==288
        and bgdma['end']<longmap['start'] and acks[obj]['clock']<longmap['start'] and r['intervals'][952]==3 and
        r['public951']<=246 and r['final_wait957']==0 and r['intervals'][908]==r['intervals'][911]==2)
    r['handoff_events']=[x for x in read(folder/'events.json') if x.get('event') in ('handoff745','reserve745','input745')]
    r.pop('prefix957')
    return r


def rejected(folder,base,log):
    failure=log.read_text(encoding='utf8',errors='replace').splitlines()
    assert failure[-1]=='AssertionError: not an empty output queue'
    assert any('test_nes_idle676.py' in l for l in failure[-5:])
    assert not (folder/'joint.json').exists()
    events=csv_groups(folder/'window.csv')
    displays=[g for g,rows in events.items() if any(r['op']==3 and r['event']=='ack' for r in rows)]
    assert displays==list(range(905,957))
    attempts=packets(folder);reference=packets(base)
    def maps(group):
        return [(g,h,b,t) for g,pack in sorted(group.items()) for h,b,t in pack if h[1]==2]
    now,old=maps(attempts),maps(reference)
    assert len(now)==len(old)==521 and all(x[:3]==y[:3] for x,y in zip(now,old))
    rgbs=list(folder.glob('frame-*.rgb'))
    assert rgbs and all(sha(f)==sha(base/f.name) for f in rgbs)
    assert (folder/'startup-clock.txt').read_bytes()==(base/'startup-clock.txt').read_bytes()
    return dict(reason=failure[-1],last_display=displays[-1],commits=len(displays),
                map_offers=len(now),changed_map_clocks=sum(x[-1]!=y[-1] for x,y in zip(now,old)),
                last_map_offer=now[-1][-1],available_RGBs=len(rgbs),final_ACK957=None,
                packets=sha(folder/'packets.jsonl'),window=sha(folder/'window.csv'))


def analyze(a):
    original,body,_,_=image(a.client)
    used=codec.BOOT+512+len(optimal(bytes(body),512))
    result=dict(stage=745,retained=727,ROM=dict(stored_B=codec.STORED,required_B=used,over_B=used-codec.STORED,
        prefix_B=512,body_B=len(body),WRAM_sha256=hashlib.sha256(body).hexdigest()),phases={},guards={})
    assert result['ROM']['over_B']==279
    for phase in (1,2):
        base=a.temp/f'nes-pair727-a{phase}'
        result['phases'][phase]={}
        for key in ('ref','arm','control','live','budget','input','matched','reserved','priced'):
            folder=base if key=='ref' else a.temp/f'nes-bg745-{key}{phase}'
            if key in ('input','priced'):
                result['phases'][phase][key]=rejected(folder,base,a.probe/f'{key}{phase}.log')
            else:
                result['phases'][phase][key]=timeline(folder,base)
    for variant,trial in [('long02',690),('normal',704),('budget-long',690),('budget-normal',704)]:
        fw=a.probe/variant/'src/obj-nes-100/firmware.stm'
        prefix='budget-' if variant.startswith('budget-') else ''
        guards={k:read(a.probe/f'{prefix}{k}-{trial}.json') for k in ('receipt742','deadline719','menu533')}
        assert all(g['firmware']==sha(fw) for g in guards.values())
        assert len(guards['receipt742']['rows'])==9 and len(guards['deadline719']['cases'])==17
        menu=guards['menu533']
        assert menu['marker_cases']==4 and len(menu['rows'])==5 and all(bool(v['released'])==(k=='normal') for k,v in menu['rows'].items())
        result['guards'][variant]=dict(firmware=sha(fw),size_B=fw.stat().st_size,free_B=212992-fw.stat().st_size,
            boundaries=[r['case'] for r in guards['receipt742']['rows']],deadline=len(guards['deadline719']['cases']),menu=list(menu['rows']))
    for name in ('long','normal'):
        sticky=read(a.probe/f'sticky-{name}.json')
        assert len(sticky['cases'])==6 and sticky['firmware']==result['guards']['budget-'+name]['firmware']
        result['guards']['budget-'+name]['sticky_progress']=sticky['cases']
        image_file=a.probe/f'input-{name}'/'src/obj-nes-100/firmware.stm'
        result['guards']['input-'+name]=dict(size_B=image_file.stat().st_size,
            free_B=212992-image_file.stat().st_size,firmware=sha(image_file))
        trial=690 if name=='long' else 704
        ordinary=read(a.probe/f'input-menu533-{trial}.json')
        deadline=read(a.probe/f'input-deadline719-{trial}.json')
        assert ordinary['firmware']==deadline['firmware']==sha(image_file)
        assert len(ordinary['rows'])==5 and len(deadline['cases'])==17
        order=read(a.probe/f'checked-{name}.json')
        assert order['firmware']==sha(image_file) and order['old_reason4_rejection']==dict(sent=17,retired=16,bulk_pending=0,SPI=[232,224])
        result['guards']['input-'+name].update(old_reason4_rejection=order['old_reason4_rejection'],
            submit_boundary=order['submit_boundary'],sticky_progress=order['cases'])
    for variants in result['phases'].values():
        assert variants['arm']['firmware']==variants['live']['firmware']==result['guards']['long02']['firmware']
        assert variants['budget']['firmware']==result['guards']['budget-long']['firmware']
        assert all(variants[k]['firmware']==variants['ref']['firmware'] for k in ('control','matched','reserved'))
    for n in (1,2):
        variants=result['phases'][n]
        for k in ('matched','reserved'):
            cur=variants[k]
            assert not cur['map_issue']['changed'] and cur['handoff_events']
        assert variants['priced']['changed_map_clocks']==0
        run=variants['live']
        order=run['order957']
        assert order['BG_DMA']['end']<order['long_map']['start'] and order['OBJ']['ack']<order['long_map']['start']
        assert order['queue_at_long_map']['nextbytes']==288
        assert order['long_map']['start']<run['scroll_push']<order['long_map']['end']
        rows=csv_groups(a.temp/f'nes-bg745-live{n}'/'window.csv')[957]
        next_event=next(e for e in rows if e['clock']>order['long_map']['end'] and e['event'] in ('load','ppu_dma'))
        assert next_event['event']=='load' and next_event['section']==5
        result['guards'][f'priority{n}']=next_event
        for mode in ('stop','stale'):
            f=a.temp/f'nes-bg745-{mode}{n}'
            result_cpu=read(f/'result.json')
            assert result_cpu['passed'] and result_cpu['commits']==52
            assert result_cpu['last_status'] in ((0,228) if mode=='stop' else (224,))
            retained=sha(f/'retained.rgb')
            assert retained==sha(a.temp/f'nes-pair727-a{n}'/'frame-956.rgb')
            result['guards'][f'{mode}{n}']=dict(commits=52,status=result_cpu['last_status'],retained_sha256=retained)
    for tag,n in [('reserved',1),('budget',2)]:
        known=result['phases'][n][tag]['OBJ_MDMAEN'][0]
        assert known['line']<=257
        negatives={}
        for fault in ('pre','during','head'):
            f=a.temp/f'nes-bg745-{tag}{n}-{fault}'
            clock=int((f/'fault745.txt').read_text())
            commit=read(f/'result.json')['commits']
            obj=[r for r in records(f/'dma745.csv') if r['g']==957 and r['src']==19104]
            if fault=='head':
                rows=csv_groups(f/'window.csv')[957]
                head=next(e for e in rows if e['clock']>clock and e['event'] in ('load','ppu_dma'))
                assert commit==53 and head['event']=='load' and head['section']==5 and len(obj)==1 and obj[0]['n']==288
            else:
                assert commit==52 and sha(f/'retained.rgb')==sha(a.temp/f'nes-pair727-a{n}'/'frame-956.rgb')
                assert [r['n'] for r in obj]==([] if fault=='pre' else [64])
                assert (clock<known['clock'])==(fault=='pre')
            negatives[fault]=dict(at=clock,commits=commit,OBJ_MDMAEN=obj)
        result['guards'][tag+str(n)]=negatives
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','client','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
