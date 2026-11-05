# SPDX-License-Identifier: MIT
"""Reconcile the payload frozen in ARM memory with SPI, 65816 and the beam deadline."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_nes_map626 import Calendar, csv_groups, deadlines, lanes, measure, ms, one, packets, read, sha, work


def trace(folder):
    cutoff=deadlines(folder)[951]['previous_cutoff']
    cpu=csv_groups(folder/'window.csv')[951]
    stream=[e for e in read(folder/'events.json') if e['generation']==951]
    sends=[e for e in stream if e.get('opcode')=='0xe1']
    commands=packets(folder)[951]
    freeze=one(stream,'frozen627')
    confirmed=bytes.fromhex(freeze['data'])
    cpu_index=one([r for r in cpu if r['op']==3],'load')['index']-len(commands)+1
    records=[]
    late=[]
    section_issue={}
    map_tail=[]
    changed={n:0 for n in (1,2,4,8)}
    mask_bytes=dict.fromkeys(changed,0)
    previous=(folder/'map-949.bin').read_bytes()
    current=(folder/'map-951.bin').read_bytes()
    beam=csv_groups(folder/'seal528.csv')
    banks=[one(beam[g],'final_credit')['bank'] for g in (949,950,951)]
    assert banks[0]==banks[2]!=banks[1]
    for i,((h,_,push),e1) in enumerate(zip(commands,sends,strict=True),cpu_index):
        op,section=h[:2]
        off=int.from_bytes(h[10:12],'little')
        assert abs(push-e1['clock'])<=1
        head=[r for r in cpu if r['index']==i]
        load=one(head,'load')
        ack=one(head,'ack')
        assert (load['op'],load['section'])==(op,section) and push<=load['clock']<=ack['clock']
        label='SEAL' if op==3 else f'{section}/{op}'
        if section==2 and off>=2048:
            map_tail.append(e1)
            raw=h[16:]
            assert op==2 and len(raw)==192 and raw==current[off:off+192]
            for n in changed:
                changed[n]+=n*sum(raw[j:j+n]!=previous[off+j:off+j+n] for j in range(0,192,n))
                mask_bytes[n]+=(192//n+7)//8
        section_issue.setdefault(label,[]).append(ms(e1['start']-cutoff))
        if e1['clock']>=cutoff:
            late.append([label,off,e1['bytes']])
        if op!=3 and (section!=5 or off<1121):
            continue
        ready,=[r for r in stream if r['event']=='payload627' and r['section']==section and r['offset']==off]
        header,=[r for r in stream if r['event']=='header627' and r['seq']==int.from_bytes(h[2:4],'little')]
        assert header['digest']==hashlib.sha256(h).hexdigest()
        clocks=dict(frozen=freeze['clock'],ready=ready['clock'],header=header['clock'],issue=e1['start'],
                    pushed=e1['clock'],head=load['clock'],ack=ack['clock'])
        assert list(clocks.values())==sorted(clocks.values())
        missing=0
        if section==5:
            data=h[16:]
            if op in (4,5):
                data*=int.from_bytes(h[14:16],'little')//2
            a=off-1121
            assert confirmed[a:a+len(data)]==data
            writes=freeze['writes'][a:a+len(data)]
            missing=writes.count(None)
            observed=[v for v in writes if v is not None]
            if observed:
                clocks['source_last']=max(observed)
                assert max(observed)<=freeze['clock']
            if a<384:
                clocks['packed']=ready['pack_last']
                assert freeze['clock']<=clocks['packed']<=ready['clock']
        records.append(dict(offset=off,op=op,B=e1['bytes'],unobserved_source_bytes=missing,
                            relative_ms={k:round(ms(v-cutoff),6) for k,v in clocks.items()}))
    assert [r['offset'] for r in records]==[1121,1187,1249,1443,1505,1745,1748,0]
    seal=sends[-1]['start']
    bus=[r for r in stream if r['event']=='SPI']
    def occupancy(end):
        occupied=sum(max(0,min(end,r['clock'])-max(freeze['clock'],r['start'])) for r in bus)
        return dict(elapsed_ms=ms(end-freeze['clock']),SPI_ms=ms(occupied))
    stages={e['event']:ms(e['clock']-cutoff) for e in stream
            if e['event'] in ('bg_map_frozen','prepare_enter','end_enter','output_enter531')}
    bulk=[r for r in cpu if r['op']==7 and r['event']=='ack']
    stages['last_tile_consumed']=ms(bulk[-1]['clock']-cutoff)
    bg=one(stream,'bg_map_frozen')['clock']
    until=freeze['clock']
    assert len(map_tail)==8 and sum(e['bytes'] for e in map_tail)==1688
    map_cost=dict(tail_wire_B=1688,previous_target_generation=949,changed_group_B=changed,mask_B=mask_bytes,
                  start_to_last_push_ms=ms(map_tail[-1]['clock']-map_tail[0]['start']),
                  bg_to_freeze_ms=ms(until-bg),bg_to_freeze_SPI_ms=ms(sum(
                      max(0,min(until,r['clock'])-max(bg,r['start'])) for r in bus)))
    return dict(previous_cutoff=cutoff,packets=records,late=late,stages_ms=stages,bus_to_cutoff=occupancy(cutoff),
                bus_to_SEAL=occupancy(seal),map=map_cost,issue_range_ms={k:[min(v),max(v)] for k,v in section_issue.items()})


def group_budget(folder):
    """Literal packets only, with the previous confirmed image of the same bank."""
    commands=packets(folder)
    beam=csv_groups(folder/'seal528.csv')
    rows={}
    last={}
    for g in range(905,958):
        bank=one(beam[g],'final_credit')['bank']
        current=(folder/f'map-{g}.bin').read_bytes()
        previous=last.get(bank)
        last[bank]=current
        saved=count=literal=0
        if previous is not None:
            for h,_,_ in commands[g]:
                if h[:2]!=b'\x02\x02':
                    continue
                offset=int.from_bytes(h[10:12],'little')
                raw=h[16:]
                assert len(raw)%64==0 and raw==current[offset:offset+len(raw)]
                literal+=len(raw)
                mask=(len(raw)//4+7)//8
                changed=sum(4 for j in range(0,len(raw),4) if raw[j:j+4]!=previous[offset+j:offset+j+4])
                if mask+changed<len(raw):
                    count+=1
                    saved+=len(raw)-mask-changed
        rows[g]=dict(cold=previous is None,literal_B=literal,shorter_packets=count,wire_saving_ceiling_B=saved)
    return rows


def run(a):
    calendar=Calendar(a.traces/'nes-service509-rom03')
    addresses=[addr for _,s in read(a.plans/'frame954/plans.json') for q in [bytes.fromhex(s)] if q[6]==0 for _,addr in lanes(q)]
    old=read(Path(__file__).resolve().parents[1]/'analysis/seal625-verification.json')
    modes=['base','control','before','after']
    images={m:(a.build.parent/'nes-seal625/tables-bg' if m=='base' else a.build/m)/'src/obj-nes-100/firmware.stm'
            for m in modes+['after-small','after-fit','after-native']}
    result=dict(Flash_B={m:f.stat().st_size for m,f in images.items()},phases=[])
    assert all(images[m].stat().st_size<=212992 for m in ('base','control','before'))
    assert all(images[m].stat().st_size>212992 for m in ('after','after-small','after-fit','after-native'))
    for i in (1,2):
        ref=a.traces/f'nes-seal625-tables-bg-{i}'
        prior=old['phases'][i-1]['tables-bg']
        assert all(sha(ref/f)==digest for f,digest in prior['pins'].items())
        original=read(ref/'joint.json')
        workload=work(ref)
        budget=group_budget(ref)
        if i==1:
            result['map_group_budget']=budget
        else:
            assert budget==result['map_group_budget']
        phase={}
        for mode in modes:
            d=a.traces/f'nes-tail627-{mode}-{i}'
            j=read(d/'joint.json')
            assert j['passed'] and j['commits']==53 and j['last_status']==1
            assert j['firmware_SHA256']==sha(images[mode]) and work(d)==workload
            assert all(j[k]==original[k] for k in ('parameters','client_SHA256','vram_DMA_B','ROM_read_allocations'))
            for g in range(905,958):
                for f in (f'map-{g}.bin',f'frame-{g}.rgb'):
                    assert sha(d/f)==sha(ref/f)
            if mode=='base':
                assert j['frames']==original['frames'] and all(sha(d/f)==sha(ref/f) for f in ('packets.jsonl','window.csv'))
            r=measure(d,calendar,addresses)
            cpu=csv_groups(d/'window.csv')
            displays={g:one([r for r in cpu[g] if r['op']==3],'reveal') for g in range(905,958)}
            shows={g:r['frame'] for g,r in displays.items()}
            early_frames=[]
            if mode in ('before','after'):
                for g,commands in packets(d).items():
                    keys=[h[1] for h,_,_ in commands]
                    if keys.index(5)<keys.index(3):
                        early_frames.append(g)
                assert 951 in early_frames
            phase[mode]=dict(source=trace(d),early_frames=early_frames,display950=shows[950],display951=shows[951],
                             intervals={g:shows[g]-shows[g-1] for g in range(951,958)},
                             dense=shows[955]-shows[950],dense_ms=ms(displays[955]['clock']-displays[950]['clock']),
                             ACK=r['last_ACK'],delta_ms=ms(r['last_ACK']-prior['last_ACK']),
                             display922=shows[922],ROM923_delta_ms=ms(r['ROM923']['response']-prior['ROM923']['response']),
                             map955=r['map955'],ROM96=r['ROM96'],display906=shows[906],wait957=r['wait957'],
                             wire_B=j['wire_B'],pins=r['pins'],firmware=j['firmware_SHA256'],client=j['client_SHA256'],
                             IRQ_calls=j['SysTick_calls'],ROM_allocations=j['ROM_read_allocations'],vram_DMA_B=j['vram_DMA_B'])
        for mode,r in phase.items():
            r['timing_pass']=all((r['dense']<phase['base']['dense'],r['intervals'][951]<phase['base']['intervals'][951],
                                   r['delta_ms']<0,r['wait957']==0,r['display922']==92,r['ROM923_delta_ms']<=0,
                                   r['intervals'][952]==r['intervals'][954]==r['intervals'][955]==4,
                                   r['display906']==9,r['ROM96']==96))
        # The first observation pass recorded final writes and serializer entry.
        # Accept extra entry hooks only when the entire original schedule matches.
        base=a.traces/f'nes-tail627-base-{i}'
        extra=a.traces/f'nes-tail627-prep-{i}'
        if not extra.exists():
            extra=base
        assert all(sha(extra/n)==sha(base/n) for n in ('window.csv','packets.jsonl','joint.json'))
        events=[e for e in read(extra/'events.json') if e['generation']==951]
        archived=[e for e in read(base/'events.json') if e['generation']==951]
        assert [e for e in events if e['event'] not in ('pack_start627','span_start627')]==[
            e for e in archived if e['event'] not in ('pack_start627','span_start627')]
        cutoff=phase['base']['source']['previous_cutoff']
        packed=one(events,'pack_start627')['clock']
        starts={e['offset']:e['clock'] for e in events if e['event']=='span_start627'}
        assert set(starts)=={0,1121,1505}
        prep={}
        for off,clock in starts.items():
            ready,=[e['clock'] for e in events if e['event']=='payload627' and e['section']==5 and e['offset']==off]
            assert clock<=ready
            prep[off]=dict(start_ms=ms(clock-cutoff),to_first_serializer_ms=ms(ready-clock))
        phase['base']['prep']=dict(first_pack_write_ms=ms(packed-cutoff),spans=prep,trace=sha(extra/'events.json'))
        result['phases'].append(phase)
    result['priority_and_independent']=read(a.traces/'nes-tail627-edges/edges.json')
    result['ARM']={m:read(a.build/m/'guards.json') for m in ('control','before','after')}
    assert all(v['firmware']==sha(images[m]) for m,v in result['ARM'].items())
    result['STOP']={m:read(a.traces/f'nes-tail627-{folder}/result.json') for m,folder in
                    (('before','stop02-before'),('after','stop-after'))}
    assert len(result['priority_and_independent'])==9
    assert all(len(rows)==4 and all(r['commits']==46 and r['status']==(0 if r.get('idle_after_retire') else 228)
                                   for r in rows) for rows in result['STOP'].values())
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','plans','build','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
