# SPDX-License-Identifier: MIT
"""Account for each accepted 955 map row through idle or sealed DMA on both clocks."""
import argparse
import json
from pathlib import Path

from analyze_nes_seal625 import Calendar, csv_groups, lanes, measure, ms, one, packets, read, sha, work
from analyze_nes_palette622 import detail
from analyze_nes_output531 import prior_blank_windows


def deadlines(folder):
    cpu=csv_groups(folder/'window.csv')
    beam=csv_groups(folder/'seal528.csv')
    events=read(folder/'events.json')
    commands=packets(folder)
    result={}
    for g in (951,952,953,954,955,957):
        seal=[r for r in cpu[g] if r['op']==3]
        previous=one([r for r in cpu[g-1] if r['op']==3],'reveal')
        displayed=one(seal,'reveal')
        anchor=next(r for r in reversed(beam[g]) if r['event']=='dma' and r['port']==4)
        first=next(r for r in seal if r['event']=='ppu_dma' and r['clock']==anchor['clock'])
        assert first['frame']==displayed['frame']
        windows=sorted(prior_blank_windows(anchor,first['frame'],previous['clock'],anchor['clock'],246))
        # If OAM starts after the decision line, the current window already
        # ended. In both cases the penultimate window is the previous blank.
        assert anchor['clock']-windows[-1][1]<16*1364 and len(windows)>=2
        cutoff=windows[-2][1]
        sends=[e for e in events if e['generation']==g and e.get('opcode')=='0xe1']
        assert sends[-1]['packet_opcode']==3 and len(commands[g])==len(sends)
        late=[]
        for e,(head,bulk,clock) in zip(sends,commands[g]):
            assert abs(e['clock']-clock)<=1
            if e['clock']>=cutoff:
                late.append(dict(op=head[0],section=head[1],offset=int.from_bytes(head[10:12],'little'),
                                 wire_B=e['bytes'],issue_minus_cutoff_ms=ms(e['start']-cutoff)))
        result[g]=dict(previous_cutoff=cutoff,SEAL_issue_minus_cutoff_ms=ms(sends[-1]['start']-cutoff),
                       SEAL_load_minus_cutoff_ms=ms(one(seal,'load')['clock']-cutoff),
                       packets_pushed_after=late,previous_display_to_SEAL_ms=ms(one(seal,'load')['clock']-previous['clock']))
    return result


def rows626(folder, expected):
    cpu=csv_groups(folder/'window.csv')
    beam=csv_groups(folder/'seal528.csv')
    idle=[]
    for i,row in enumerate(cpu[955]):
        if row['event']=='idle524' and row['value']>=65536:
            first=one(cpu[955][i+1:i+2],'ppu_dma')
            last=one(cpu[955][i+2:i+3],'ppu_last')
            assert first['frame']==last['frame'] and 225<=first['line']<=last['line']<262
            idle.append((row['value']-65536,first['value']))
    sealed=[]
    for r in beam[955]:
        base=0xa000 if r['bank'] else 0x6000
        if r['event']=='dma' and r['port']==24 and base<=r['dst']<base+4096:
            sealed.append((r['dst']-base,r['bytes']))
    def expand(ranges):
        assert all(off%64==size%64==0 and size and off+size<=4096 for off,size in ranges)
        return [row for off,size in ranges for row in range(off,off+size,64)]
    early_rows=expand(idle)
    late_rows=expand(sealed)
    assert sorted(early_rows+late_rows)==expected and len(set(expected))==len(expected)
    seals={g:[r for r in cpu[g] if r['op']==3] for g in range(905,958)}
    shows={g:one(rows,'reveal')['frame'] for g,rows in seals.items()}
    for g,rows in seals.items():
        ack=one(rows,'ack')
        assert ack['frame']==shows[g] and ack['value']==1
    final=one(seals[955],'final212')
    latches=[r['line'] for r in beam[955] if r['event']=='latch' and r['clock']>=final['clock']]
    return dict(idle=idle,sealed=sealed,sealed_B=64*len(late_rows),early_B=64*len(early_rows),
                early_tail_B=64*len(set(early_rows)&set(range(3200,3584,64))),
                dense=shows[955]-shows[950],intervals={g:shows[g]-shows[g-1] for g in (952,954,955,957)},
                display922=shows[922],final_entry955=final['line'],final_latches955=latches,display955=shows[955],
                ack955=one(seals[955],'ack')['clock'],last_ACK=one(seals[957],'ack')['clock'],
                trace=sha(folder/'window.csv'))


def extended_grants(folder):
    result=[]
    for g,rows in csv_groups(folder/'window.csv').items():
        for i,r in enumerate(rows):
            if r['event']=='idle524' and r['value']>=65536:
                first=one(rows[i+1:i+2],'ppu_dma')
                if first['value']>1152:
                    last=one(rows[i+2:i+3],'ppu_last')
                    assert first['value']==1344 and last['frame']==first['frame']
                    assert 225<=first['line']<=last['line']<262
                    result.append(dict(g=g,offset=r['value']-65536,line=first['line'],end=last['line']))
    return result


def analyze(a):
    calendar=Calendar(a.traces/'nes-service509-rom03')
    addresses=[v for _,h in read(a.plans/'frame954/plans.json') for q in [bytes.fromhex(h)] if q[6]==0 for _,v in lanes(q)]
    archive=read(a.reference)
    phases=[]
    costs={m:(a.build/m/'src/obj-nes-100/firmware.stm').stat().st_size for m in ('order','compact')}
    assert costs['compact']<=212992<costs['order']
    for i in (1,2):
        base=a.traces/f'nes-seal625-tables-bg-{i}'
        old=archive['phases'][i-1]['tables-bg']
        assert all(sha(base/f)==digest for f,digest in old['pins'].items())
        j=read(base/'joint.json')
        expected=sorted(row for h,_,_ in packets(base)[955] if h[1]==2 for row in range(
            int.from_bytes(h[10:12],'little'),int.from_bytes(h[10:12],'little')+
            int.from_bytes(h[12:14] if h[0]==2 else h[14:16],'little'),64))
        closed={}
        for mode in ('base','suffix','order','joint','wide','selected'):
            folder=base if mode=='base' else a.traces/f'nes-map626-{mode}-{i}'
            joint=read(folder/'joint.json')
            assert all(joint[k]==j[k] for k in ('parameters','vram_DMA_B','ROM_read_allocations'))
            assert joint['firmware_SHA256']==(j['firmware_SHA256'] if mode not in ('order','joint') else sha(a.build/'compact/src/obj-nes-100/firmware.stm'))
            client=a.build/(mode if mode in ('wide','selected') else 'client')/'sink165.sfc'
            assert joint['client_SHA256']==(j['client_SHA256'] if mode in ('base','order') else sha(client))
            assert work(folder)==work(base)
            assert all(sha(folder/f)==sha(base/f) for g in range(905,958) for f in (f'frame-{g}.rgb',f'map-{g}.bin'))
            r=rows626(folder,expected)
            q=measure(folder,calendar,addresses)
            r['extended']=extended_grants(folder)
            if mode not in ('wide','selected'):
                assert not r['extended']
            else:
                observed=a.traces/(f'nes-map626-fallback-{i}' if mode=='selected' else f'nes-map626-observe-{mode}-{i}')
                assert read(observed/'audit.json')['trace']==r['trace']
                r['selection955']=[dict(zip(('sample_line','accepted_B','issued_B','offset','fallback'),
                                            map(int,line.split(',')),strict=True))
                                   for line in (observed/'wide955.csv').read_text().splitlines()]
                if mode=='selected':
                    r['fallback_grants']=[dict(zip(('generation','line','B','offset'),map(int,line.split(',')),strict=True))
                                          for line in (observed/'fallback.csv').read_text().splitlines()]
                    assert any(v['generation']==926 and v['B']==1344 for v in r['fallback_grants'])
            maps=[int.from_bytes(h[10:12],'little') for h,_,_ in packets(folder)[955] if h[1]==2]
            old_order=[320,512,896,2048,2240,2432,2624,2816,3008,3200,3392]
            swapped_order=old_order[:3]+[2240,2048]+old_order[5:]
            assert maps==(swapped_order if mode in ('order','joint') else old_order)
            r.update(wait957=q['wait957'],grants957=detail(folder)['grants'],same_blank957=q['same_blank957'],
                     map_order955=maps,first_map955=q['map955'][0],ROM96=q['ROM96'],display906=q['display906'],
                     ROM923_delta_ms=ms(q['ROM923']['response']-old['ROM923']['response']),pins=q['pins'],
                     budgets=deadlines(folder),wire_B=joint['wire_B'],ACK_delta_ms=ms(r['last_ACK']-old['last_ACK']))
            r['pass']=bool(r['display922']==92 and r['ROM923_delta_ms']<=0 and r['display906']==9 and r['ROM96']==96
                           and r['intervals'][952]==r['intervals'][954]==r['intervals'][955]==4 and r['dense']<=20
                           and r['first_map955']>=192 and r['early_tail_B']==384 and r['wait957']==0
                           and r['same_blank957'] and r['ACK_delta_ms']<=0)
            closed[mode]=r
        fixed={}
        for mode in ('front','swap','back','both','wide','selected'):
            folder=a.traces/f'nes-map626-fixed-{mode}-{i}'
            audit=read(folder/'audit.json')
            assert audit['frames']==53 and audit['source']==sha(base/'packets.jsonl') and audit['trace']==sha(folder/'window.csv')
            r=rows626(folder,expected)
            r.update(ACK_delta_ms=ms(r['last_ACK']-old['last_ACK']),replay=audit)
            fixed[mode]=r
        assert fixed['front']['trace']==closed['base']['trace']
        phases.append(dict(fixed=fixed,closed=closed))
    data=dict(phases=phases,Flash_B=costs,ARM=read(a.build/'arm-guards.json'),
               CPU={m:read(a.build/m/'build.json') for m in ('client','wide','selected')},edges=read(a.traces/'nes-map626-edges/edges.json'),
               beam_edges=read(a.traces/'nes-map626-wide-edges/result.json'),
               suffix_edges=read(a.traces/'nes-map626-suffix-edges02/result.json'),
              STOP=read(a.traces/'nes-map626-stop/result.json')+read(a.traces/'nes-map626-raw-stop/result.json'),
              pass_both={m:all(p['closed'][m]['pass'] for p in phases) for m in ('suffix','order','joint','wide','selected')})
    data['wide_edges']=read(a.traces/'nes-map626-wide-edges-base/edges.json')
    data['wide_STOP']=read(a.traces/'nes-map626-wide-stop/result.json')+read(a.traces/'nes-map626-wide-raw-stop/result.json')
    data['selected_edges']=read(a.traces/'nes-map626-selected-edges/edges.json')
    data['selected_beam']=read(a.traces/'nes-map626-selected-beam/result.json')
    data['selected_STOP']=read(a.traces/'nes-map626-selected-stop/result.json')+read(a.traces/'nes-map626-selected-raw-stop/result.json')
    assert len(data['edges'])==len(data['wide_edges'])==len(data['selected_edges'])==9
    for suite in ('STOP','wide_STOP','selected_STOP'):
        assert len(data[suite])==12 and all(r['status']==0xe4 for r in data[suite])
    a.out.write_text(json.dumps(data,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','traces','plans','reference','out'):
        p.add_argument('--'+name,type=Path,required=True)
    analyze(p.parse_args())
