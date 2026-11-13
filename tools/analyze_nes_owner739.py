# SPDX-License-Identifier: MIT
"""Separate material readiness, staging ownership, four-slot queue and consumer time."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_seal686 import receive_batch
from analyze_nes_dma542 import partition
from analyze_nes_prefix736 import audit, csv_groups, map_image, ms, packets, read, resources, section5, sha, tile_image


def marks(folder, observer):
    cpu=csv_groups(folder/'window.csv')
    events=[e for e in read(folder/'events.json') if e['generation']==957]
    prod=read(folder/'obj-phases.json')['957']
    with (observer/'owner.csv').open() as f:
        taps=[{k:(v if k=='event' else int(v)) for k,v in r.items()} for r in csv.DictReader(f)]
    assert read(observer/'audit.json')['matched_events']==sum(len(v) for v in cpu.values())
    rows=cpu[957]
    loads=[r for r in rows if r['event']=='load']
    acks=[r for r in rows if r['event']=='ack']
    heads=packets(folder)[957]
    assert len(heads)==len(loads)==len(acks)
    i=next(i for i in reversed(range(len(heads))) if heads[i][0][:2]==bytes([7,1]))
    h,bulk,push=heads[i]
    assert len(bulk)==288 and int.from_bytes(h[10:12],'little')==2720
    token=int.from_bytes(h[16:20],'little')
    bg=next(e for e in taps if e['event']=='bank_release' and e['value']==token-1)
    own=next(e for e in taps if e['event']=='bank_release' and e['value']==token)
    # END is the final entry in the last plan bank. The 557 decoder advances
    # at CHECK+1, then 506 publishes the open OBJ job before setting end.
    bank=prod['banks557'][-1]
    assert bank['decoded']==bank['count'] and bank['seal']==prod['end_accepted']
    sealed=bank['release']+1
    eligible=max(sealed,bg['clock'])
    qr=next(e for e in events if e.get('opcode')=='0xe8'
            and bytes.fromhex(e['reply'])[6:18]==b'\1\1'+h[14:16]+h[10:12]+h[8:10]+h[16:20])
    submit=next(e for e in events if e.get('opcode')=='0xe1' and abs(e['clock']-push)<1)
    assert prod['last_obj_rom_response']<=sealed and eligible<qr['clock']<=submit['start']<=push<=loads[i]['clock']<own['clock']<=acks[i]['clock']
    # Physical occupancy from actual PUSH and 65816 ACK edges; never infer
    # a full queue from an old ARM snapshot.
    def occupied(t):
        return sum(t0<=t<r['clock'] for (_,_,t0),r in zip(heads,acks))
    boundaries={eligible,qr['clock']}
    for (_,_,t0),r in zip(heads,acks):
        boundaries.update(t for t in (t0,r['clock']) if eligible<t<qr['clock'])
    spans=sorted(boundaries)
    residency=[0]*5
    for a,b in zip(spans,spans[1:]):
        depth=occupied((a+b)/2)
        assert 0<=depth<=4
        residency[depth]+=b-a
    assert abs(sum(residency)-(qr['clock']-eligible))<1e-4
    arm=next(e for e in events if e['event']=='call673' and e.get('op')==23 and e['section']==1 and e['offset']==2720)
    grant=next(e for e in events if e['event']=='wire664' and e['section']==1 and e['offset']==2720)
    previous=next(r['clock'] for r in cpu[956] if r['event']=='reveal')
    checks=[e for e in events if e['event']=='owner688_return' and eligible<e['clock']<qr['start']]
    map_heads=[(h0,t0) for h0,_,t0 in heads if h0[1]==2 and eligible<=t0<=qr['clock']]
    credit=[e for e in events if e.get('opcode')=='0xe0' and eligible<e['clock']<qr['clock']]
    spi={}
    for e in events:
        if e['event']=='SPI':
            overlap=max(0,min(qr['start'],e['clock'])-max(eligible,e['start']))
            if overlap:spi[e['opcode']]=spi.get(e['opcode'],0)+overlap
    assert sum(spi.values())<=qr['start']-eligible+1
    spi['outside_SPI']=qr['start']-eligible-sum(spi.values())
    oam_i=next(i for i,(v,_,_) in enumerate(heads) if v[:2]==bytes([9,4]))
    proof=next(e for e in taps if e['event']=='proven635')
    assert loads[oam_i]['clock']<=proof['clock']<acks[oam_i]['clock']
    prefix=audit(folder)['frames']
    def reveal(g):
        return next(r for r in cpu[g] if r['event']=='reveal')
    def ack(g):
        return next(r for r in cpu[g] if r['op']==3 and r['event']=='ack')
    # Budget latch reports the exact SNES beam master hclock. Use the idle
    # VBlank after the last accepted map, even if a candidate splits the DMA.
    with (folder/'budget685.csv').open() as f:
        beams=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(f) if r['generation']=='957']
    lastmap=next(a['clock'] for (v,_,_),a in zip(heads,acks) if v[1]==2 and int.from_bytes(v[10:12],'little')==3392)
    # Reference opportunity is the second VBlank after the 956 reveal.
    # Resolve its line 246 from any measured beam in this run, not from the
    # candidate's possibly delayed map ACK. NTSC short pre-render lines are
    # outside the [225, 252] anchor and deadline in the same VBlank.
    target_frame=reveal(956)['frame']+2
    all_dma=[r for r in rows if r['event']=='ppu_dma' and r['frame']==target_frame and 225<=r['line']<=252]
    # $2137 -> budget callback -> PPU DMA. The budget callback can precede
    # the first PPU write; associate it with that beam's actual frame.
    anchors=[]
    for b in beams:
        if 225<=b['line']<=252 and any(0<=d['clock']-b['latch_clock']<6000 for d in all_dma):
            anchors.append(b['latch_clock']-b['h']+(247-b['line'])*1364)
    anchors.extend(e['clock']-e['value']+(247-e['line'])*1364 for e in taps
                   if e['event']=='beam' and e['frame']==target_frame)
    if not anchors:
        # An expired opportunity may have no idle upload at all. Use any
        # event with beam hclock in the matching frame; clock proximity to
        # the preceding reveal conservatively selects this specific blank.
        with (folder/'seal528.csv').open() as f:
            for d in csv.DictReader(f):
                t=int(d['clock']);line=int(d['line'])
                if 225<=line<=252 and abs(t-(previous+2*357368))<28000:
                    anchors.append(t-int(d['h'])+(247-line)*1364)
    cutoff=(anchors[0] if anchors else None)
    if anchors: assert max(anchors)-min(anchors)<=4,anchors
    def margin(t):
        return None if cutoff is None else ms(cutoff-t)
    stages=dict(last_source=prod['last_obj_rom_response'],OBJ_staged=sealed,previous_BG_token=bg['clock'],
                query_start=qr['start'],descriptor_checked=qr['clock'],OBJ_E1_start=submit['start'],OBJ_enqueued=push,
                OBJ_loaded=loads[i]['clock'],OBJ_token=own['clock'],OBJ_ACK=acks[i]['clock'],
                OAM_loaded=loads[oam_i]['clock'],OAM_proven=proof['clock'],OAM_ACK=acks[oam_i]['clock'],last_map_ACK=lastmap)
    burst=next((d for d in prefix[957]['prefix_map_DMA'] if d['offset']==2048 and d['bytes']==1536),None)
    if burst:stages['map1536_DMA_start']=burst['clock']
    st=submit['start']
    dma_end=next((r['clock'] for r in rows if 'map1536_DMA_start' in stages and r['event']=='ppu_last' and r['clock']>stages['map1536_DMA_start']),None)
    if dma_end:stages['map1536_DMA_end']=dma_end
    joint=read(folder/'joint.json')
    assert joint['passed'] and joint['commits']==53 and joint['max_bulk_banks']<=2
    stages['SEAL_loaded']=next(r['clock'] for r in loads if r['op']==3)
    return dict(final957=partition(folder)[957],ticks=stages,scope_inputs=dict(arm=joint['firmware_SHA256'],client=joint['client_SHA256'],
            instructions=joint['ARM_instructions'],IRQ=joint['SysTick_calls'],wire_B=joint['wire_B'],banks=joint['max_bulk_banks']),
        seven_blocks=receive_batch(folder)['checked_blocks_before_ACK'],
        stages911={r['event']:r['line'] for r in cpu[911] if r['op']==3 and r['event'] in ('load','upload165_entry')},
        after_956_reveal_ms={k:round(ms(v-previous),6) for k,v in stages.items()},
        eligible_to_query_ms={k:ms(v) for k,v in spi.items()},bank_token=token,
        queue_depth_residence_ms=[round(ms(t),6) for t in residency],queue_depth_at_OBJ_E1=occupied(st),
        ARM_outstanding_at_OBJ_call=arm['sent']-arm['retired'],ARM_outstanding_at_OBJ_wire=grant['sent']-grant['retired'],
        map_pushes_while_eligible=len(map_heads),map_progress_returns_while_eligible=len(checks),
        E0_queries_while_eligible=len(credit),source_classes=sorted({r[-1] for r in prod['cache611'] if r[0]==1}),
        occupied_BG_ms=ms(eligible-sealed),ready_head_to_E8_start_ms=ms(qr['start']-eligible),
        deadline_line247_start=cutoff,margin_to_end_of_line246_ms={k:margin(stages[k]) for k in ('OBJ_loaded','OBJ_ACK','OAM_proven','OAM_ACK','last_map_ACK','SEAL_loaded')},
        protected_DMA={g:prefix[g]['prefix_map_DMA'] for g in (952,956,957)},
        intervals={g:dict(ms=ms(reveal(g)['clock']-reveal(g-1)['clock']),VBlank=reveal(g)['frame']-reveal(g-1)['frame']) for g in (908,911,951,952,953,954,955,956,957)},
        seal_ms=ms(next(r['clock'] for r in loads if r['op']==3)-previous),line951=reveal(951)['line'],
        dense_ms=ms(reveal(957)['clock']-reveal(951)['clock'])/6,dense951_955_ms=ms(reveal(955)['clock']-reveal(950)['clock'])/5,
        last_ACK_clock=ack(957)['clock'],map1536={g:any(r['offset']==2048 and r['bytes']==1536 for r in prefix[g]['prefix_map_DMA']) for g in (952,957)},
        input_sha256={name:sha(folder/name) for name in ('window.csv','events.json','packets.jsonl','obj-phases.json','joint.json','budget685.csv')},
        owner_sha256=sha(observer/'owner.csv'))


def run(temp,probe):
    result=dict(stage=739,phases={},builds={})
    for phase in (1,2):
        paths={k:temp/(f'nes-pair727-a{phase}' if k=='ref' else f'nes-owner739-{k}{phase}') for k in ('ref','a','b')}
        ref=paths['ref']
        def work(p):
            plans=[(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
            assert plans
            colors=[(g,h[:2],h[10:]) for g,stream in packets(p).items() for h,_,_ in stream if h[1] in (3,4)]
            return map_image(p),tile_image(p),section5(p),plans,colors
        original=work(ref)
        base=None
        for k,p in paths.items():
            if k!='ref':assert work(p)==original
            obs=temp/f'nes-owner739-{k}{phase}-trace'
            for g in range(905,958):assert sha(p/f'frame-{g}.rgb')==sha(ref/f'frame-{g}.rgb')
            m=marks(p,obs)
            if base is None:base=m
            m['delta_dense_ms']=m['dense_ms']-base['dense_ms']
            m['delta_ACK_ms']=ms(m['last_ACK_clock']-base['last_ACK_clock'])
            m['passed_requested_timing']=(all(m['map1536'].values()) and
                all(m['margin_to_end_of_line246_ms'][point] is not None and
                    m['margin_to_end_of_line246_ms'][point]>=0 for point in ('OBJ_loaded','OAM_proven')) and
                m['delta_dense_ms']<0 and m['delta_ACK_ms']<0)
            result['phases'].setdefault(phase,{})[k]=m
    for build in ('arm02','normal-a','arm-b','normal-b'):
        build_info=resources(probe/build/'src')
        guards={}
        for test in ('menu','admission','deadline','issue'):
            log=probe/f'{test}-{build}.json'
            j=read(log)
            assert j['firmware']==build_info['firmware']
            guards[test]={'sha256':sha(log),'counts':{k:len(v) for k,v in j.items() if isinstance(v,(list,dict))}}
        build_info['guards']=guards
        result['builds'][build]=build_info
    result['receiver_faults']={}
    for tag in ('ref','a','b'):
        for mode in ('stop','stale'):
            suffix='stop-held' if (tag,mode)==('ref','stop') else mode
            path=temp/f'nes-owner739-{tag}1-{suffix}'
            j=read(path/'result.json')
            ref=temp/'nes-pair727-a1' if tag=='ref' else temp/f'nes-owner739-{tag}1'
            assert j['passed'] and j['commits']==52 and sha(path/'retained.rgb')==sha(ref/'frame-956.rgb')
            assert j['last_status'] in ((0,228) if mode=='stop' else (224,))
            result['receiver_faults'][f'{tag}-{mode}']=dict(commits=52,last_status=j['last_status'],pixel=sha(path/'retained.rgb'))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','probe','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.temp,a.probe),indent=2)+'\n',encoding='utf8')
