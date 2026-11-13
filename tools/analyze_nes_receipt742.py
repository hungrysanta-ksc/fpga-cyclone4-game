"""Validate matched 957 replays separately from the complete linked M4 schedules."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_beam741 import measure, records
from analyze_nes_owner739 import csv_groups, ms, packets, read, sha
from replay_nes_gap740 import schedule


def cpu_frame(folder, g):
    rows=csv_groups(folder/'window.csv')[g]
    prefix=[]
    for i,r in enumerate(rows):
        if r['event']!='idle524':
            continue
        dma=next(s for s in rows[i+1:] if s['event']=='ppu_dma')
        done=next(s for s in rows[i+1:] if s['clock']>dma['clock'] and s['event']=='ppu_last')
        assert 225<=dma['line']<=done['line']<=261 and dma['frame']==done['frame']
        prefix.append(dict(offset=r['value'],size=dma['value'],start=dma['clock'],end=done['clock'],
                           first_line=dma['line'],last_line=done['line']))
    def seal(kind):
        return next(r for r in rows if r['op']==3 and r['event']==kind)
    return {'reveal':seal('reveal'),'ACK':seal('ack')['clock'],'prefix':prefix,'final_wait':
            sum(r['event']=='wait169' and r['clock']>seal('final212')['clock'] for r in rows)}


def whole(folder,base,*,expected_client_sha=None):
    j=read(folder/'joint.json')
    orig=read(base/'joint.json')
    assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2 and j['map_WRAM_VRAM_verified']
    assert j['parameters']==orig['parameters'] and j['client_SHA256']==(expected_client_sha or orig['client_SHA256'])
    assert all(sha(folder/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,958))
    expected=packets(base)
    heads=packets(folder)
    for g in range(905,958):
        def workload(group):
            # Exclude only the frame-local issue sequence; count multiplicity.
            return Counter((h[:2]+h[4:],bytes(payload)) for h,payload,_ in group)
        assert workload(heads[g])==workload(expected[g]),g
    frames={g:cpu_frame(folder,g) for g in (907,908,910,911,950,951,952,953,954,955,956,957)}
    delta_vb={g:frames[g]['reveal']['frame']-frames[g-1]['reveal']['frame'] for g in (908,911,951,952,953,954,955,956,957)}
    cpu=csv_groups(folder/'window.csv')[957]
    loads=[r for r in cpu if r['event']=='load']
    acks=[r for r in cpu if r['event']=='ack']
    target=heads[957]
    assert len(loads)==len(acks)==len(target)
    obj=max(i for i,(h,b,_) in enumerate(target) if h[:2]==bytes((7,1)))
    oam=next(i for i,(h,_,_) in enumerate(target) if h[:2]==bytes((9,4)))
    row=max(i for i,(h,_,_) in enumerate(target) if h[1]==2)
    scroll=next(i for i,(h,_,_) in enumerate(target) if h[1]==5)
    events=[e for e in read(folder/'events.json') if e.get('event')=='SPI' and e['generation']==957]
    desc=next(e for e in events if e['opcode']=='0xe8' and bytes.fromhex(e['reply'])[6:18]==
              bytes((1,1))+target[obj][0][14:16]+target[obj][0][10:12]+target[obj][0][8:10]+target[obj][0][16:20])
    issue=[e for e in events if target[row][2]<e['clock']<=target[obj][2]+1]
    ps={g:any(x['offset']==67584 and x['size']==1536 for x in frames[g]['prefix']) for g in (952,957)}
    # The tile tap binds the DMA grant to its exact WRAM source. Convert
    # the grant to the separate MDMAEN event before testing scanline 257.
    tile=[r for r in records(folder/'tile532.csv') if r['g']==957 and 19104<=r['src']<19392]
    obj_dmas=[next(x for x in frames[957]['prefix'] if x['start']>=r['clock']) for r in tile]
    assert len({x['start'] for x in obj_dmas})==len(tile) and all(x['size']==r['n'] for x,r in zip(obj_dmas,tile))
    starts=[x['first_line'] for x in obj_dmas]
    final=[r for r in records(folder/'seal528.csv') if r['g']==957 and r['event']=='dma' and 19104<=r['src']<19392]
    assert sum(r['n'] for r in tile)+sum(r['bytes'] for r in final)==288
    dense=ms(frames[957]['reveal']['clock']-frames[951]['reveal']['clock'])/6
    ref=read(Path('analysis/owner739-verification.json'))['phases']['1' if j['parameters']['start']==7288416 else '2']['ref']
    metrics=dict(dense_ms=dense,dense_delta_us=1000*(dense-ref['dense_ms']),
                 final_ACK=frames[957]['ACK'],ACK_delta_us=ms(frames[957]['ACK']-ref['last_ACK_clock'])*1000)
    return dict(**metrics, intervals=delta_vb, public951=frames[951]['reveal']['line'], final_wait957=frames[957]['final_wait'],
                long_map=ps, OBJ_prefix_lines=starts, OBJ_final_B=sum(r['bytes'] for r in final),
                meets=all(ps.values()) and bool(starts) and min(starts)<=257 and metrics['dense_delta_us']<0 and metrics['ACK_delta_us']<0,
                map_last_push=target[row][2],map_last_ACK=acks[row]['clock'],descriptor_query=round(desc['start']),
                OBJ_push=target[obj][2],OBJ_load=loads[obj]['clock'],OBJ_ACK=acks[obj]['clock'],
                OAM_push=target[oam][2],OAM_ACK=acks[oam]['clock'],scroll_push=target[scroll][2],
                SPI_after_map_through_OBJ=dict(Counter(e['opcode'] for e in issue)),
                after_OAM_before_scroll=ms(target[scroll][2]-acks[oam]['clock']),prefix957=frames[957]['prefix'],
                firmware=j['firmware_SHA256'],ARM_instructions=j['ARM_instructions'],wire_B=j['wire_B'],
                ROM_reads=j['ROM_read_allocations'],max_bulk_banks=j['max_bulk_banks'],
                pins={k:sha(folder/k) for k in ('window.csv','packets.jsonl','events.json','joint.json','tile532.csv','seal528.csv')})


def analyze(a):
    result={'stage':742,'timing_reference':727,'board':'707D','linked_client':694,
            'scope':'Linked Cortex-M4 and executed 65816, modeled SPI/IRQ/ROM calendar; fixed-offer and oracle trials reported separately.',
            'phases':{}}
    for n in (1,2):
        base=a.temp/f'nes-pair727-a{n}'
        ref=read(Path('analysis/owner739-verification.json'))['phases'][str(n)]['ref']
        fixed={}
        for k in ('poll-firstN-actual','poll-originalN','poll-originalN-694','floor-originalN'):
            f=a.temp/('nes-receipt742-'+k.replace('N',str(n))+('-aligned' if k.startswith('floor') else ''))
            r=measure(f,base,ref,n)
            detail=read(f/'receipt742.json')
            rows=csv_groups(f/'window.csv')[957]
            ack=[x for x in rows if x['event']=='ack' and x['section']==2][-1]['clock']
            assert detail['E0_starts'][-1]>ack and all(t<ack for t in detail['E0_starts'][:-1])
            if k.startswith('floor'):
                assert detail['E0_starts'][-1]==ack+1
            detail['actual_map_ACK']=ack
            if k=='poll-firstN-actual':
                pulse=int((f/'pulse741.txt').read_text().splitlines()[0])
                assert abs(r['scroll_push']-pulse-schedule(base,n,'first')['callback_masterclocks'])<=1
            fixed[k]=dict(**detail,ACK_delta_us=r['ACK_delta_us'],dense_delta_us=r['dense_delta_us'],
                          OBJ_prefix_B=r['OBJ_prefix_B'],OAM_margin_us=r['OAM_ACK_before_247_us'],prefix=r['prefix_after_OAM'])
        sensitivity={}
        for lead in (1364,2728,4092):
            f=a.temp/f'nes-receipt742-floor-original{n}-lead{lead}-aligned'
            r=measure(f,base,ref,n)
            tile=[t for t in records(f/'tile532.csv') if t['g']==957 and t['src']==19104]
            starts=[next(p['lines'][0] for p in r['prefix_after_OAM'] if p['start']>=t['clock']) for t in tile]
            assert sum(t['n'] for t in tile)==r['OBJ_prefix_B']
            sensitivity[lead]=dict(OBJ_prefix_B=r['OBJ_prefix_B'],OBJ_DMA_start_lines=starts,
                                   ACK_delta_us=r['ACK_delta_us'],dense_delta_us=r['dense_delta_us'],
                                   both_long_map=any(p['size']==1536 for p in r['prefix_after_OAM']))
        probe=a.temp/f'nes-receipt742-poll-original{n}-ranges'
        orig=a.temp/f'nes-receipt742-poll-original{n}'
        assert sha(probe/'window.csv')==sha(orig/'window.csv') and read(probe/'audit.json')['frames']==53
        taps=records(probe/'owner.csv')
        desc=[e['clock'] for e in taps if e['event']=='descriptor742']
        bulk=[e['clock'] for e in taps if e['event']=='bulk742']
        assert len(desc)==12 and len(bulk)==3 and desc[-1]<bulk[0]<bulk[-1]
        phases={event:[e['clock'] for e in taps if e['event']==event] for event in
                ('mark212','bits212','append212','append_new212','merge532')}
        sensitivity['source_read']=dict(descriptor_last=desc[-1],bulk_first=bulk[0],bulk_last=bulk[-1],
            pre_read_us=1000*ms(bulk[0]-desc[-1]),first_to_last_us=1000*ms(bulk[-1]-bulk[0]),
            code_marks=phases,tap_sha256=sha(probe/'owner.csv'))
        candidate=whole(a.temp/f'nes-receipt742-final{n}',base)
        result['phases'][n]=dict(base=whole(base,base),candidate=candidate,fixed=fixed,sensitivity=sensitivity)
    baseline_guards=read(a.probe/'guard727.json')
    assert baseline_guards['firmware']==result['phases'][1]['base']['firmware']
    result['baseline_guard_SPI']={r['case']:r['SPI'] for r in baseline_guards['rows']}
    for trial,folder in [(690,'final-long'),(704,'final-normal')]:
        guard,menu,deadline=[read(a.probe/f'{k}-{trial}.json') for k in ('receipt742','menu533','deadline719')]
        image=a.probe/folder/'src/obj-nes-100/firmware.stm'
        assert guard['firmware']==menu['firmware']==deadline['firmware']==sha(image)
        assert len(guard['rows'])==9 and len(deadline['cases'])==17 and menu['marker_cases']==4 and len(menu['rows'])==5
        assert all(bool(v['released'])==(k=='normal') for k,v in menu['rows'].items())
        result[str(trial)]=dict(firmware=sha(image),flash_B=image.stat().st_size,guards=guard['rows'],menu=list(menu['rows']))
    assert result['690']['firmware']==result['phases'][1]['candidate']['firmware']==result['phases'][2]['candidate']['firmware']
    for mode,code in [('stop',0),('stale',224)]:
        f=a.temp/('nes-receipt742-poll-original1-'+mode)
        j=read(f/'result.json')
        assert j['passed'] and j['last_status']==code and j['commits']==52
        assert sha(f/'retained.rgb')==sha(a.temp/'nes-pair727-a1/frame-956.rgb')
        result[mode]=dict(commits=52,status=code)
    f=a.temp/'nes-receipt742-poll-original1-head'
    now,old=map(int,(f/'fault741.txt').read_text().split())
    head=next(r for r in csv_groups(f/'window.csv')[957] if r['clock']>now and r['event'] in ('load','ppu_dma'))
    assert head['event']=='load' and head['section']==5 and now<old and read(f/'audit.json')['frames']==53
    result['priority']=head
    result['meets_both_phases']=all(p['candidate']['meets'] for p in result['phases'].values())
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
