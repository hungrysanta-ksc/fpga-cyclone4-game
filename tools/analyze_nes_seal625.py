# SPDX-License-Identifier: MIT
"""Match production, acceptance and PPU use at the 955 display boundary."""
import argparse
import json
from pathlib import Path

from analyze_nes_bank621 import Calendar, csv_groups, lanes, ms, one, read, sha, work
from analyze_nes_raw624 import measure
from analyze_nes_output615 import packets
from analyze_nes_palette622 import detail


def trace955(folder):
    cpu=csv_groups(folder/'window.csv')
    seal=[r for r in cpu[955] if r['op']==3]
    origin=one([r for r in cpu[954] if r['op']==3],'reveal')['clock']
    commands=packets(folder)[955]
    spi=[e for e in read(folder/'events.json') if e['generation']==955 and e['event']=='SPI']
    pushes=[e for e in spi if e['opcode']=='0xe1']
    assert len(pushes)==len(commands)
    accepted={r['index']:r for r in cpu[955] if r['event']=='ack'}
    end=one(seal,'load')['index']
    first=next(r for r in csv_groups(folder/'seal528.csv')[955] if r['event']=='dma' and r['port']==24)
    map_base=0xa000 if first['bank'] else 0x6000
    obj_base=0x8000 if first['bank'] else 0x4000
    bg_base=0xc000 if first['bank'] else 0
    if map_base<=first['dst']<map_base+4096:
        first_section,base=2,map_base
    elif obj_base<=first['dst']<obj_base+4096:
        first_section,base=1,obj_base
    else:
        first_section,base=0,bg_base
        assert bg_base<=first['dst']<bg_base+16384
    required=set(range(first['dst']-base,first['dst']-base+first['bytes']))
    sources=[]
    tail=[]
    for idx,((h,bulk,clock),e) in enumerate(zip(commands,pushes),end-len(commands)+1):
        assert abs(clock-e['clock'])<=1
        ack=accepted[idx]
        assert (ack['op'],ack['section'])==(h[0],h[1]) and clock<=ack['clock']
        off=int.from_bytes(h[10:12],'little')
        n=int.from_bytes(h[12:14] if h[0]==2 else h[14:16],'little')
        if h[1]==first_section and h[0] in (2,4,5,6,7) and required.intersection(range(off,off+n)):
            sources.append(dict(offset=off,B=n,issue=e['start'],push=clock,accepted=ack['clock']))
            required.difference_update(range(off,off+n))
        tail.append(dict(op=h[0],section=h[1],offset=off,B=len(h),bulk_B=len(bulk),
                         issue_ms=ms(e['start']-origin),push_ms=ms(clock-origin),accept_ms=ms(ack['clock']-origin)))
    assert not required and max(x['accepted'] for x in sources)<first['clock']
    plans=read(folder/'obj-phases.json')['955']
    reads=plans['cache611']
    grants=[r for r in reads if r[-1]=='ROM']
    assert grants[-1][0]==0
    early_map=[]
    for i,row in enumerate(cpu[955]):
        if row['event']=='idle524' and row['value']>=65536:
            dma=one(cpu[955][i+1:i+2],'ppu_dma')
            end=one(cpu[955][i+2:i+3],'ppu_last')
            following=cpu[955][i+3]
            early_map.append(dict(offset=row['value']-65536,B=dma['value'],
                                  line=dma['line'],end_line=end['line'],ms=ms(dma['clock']-origin),
                                  following={k:following[k] for k in ('event','op','section','line')}))
    assert all(225<=r['line']<262 for r in seal if r['event'] in ('ppu_dma','ppu_last','reveal'))
    return dict(origin=origin,tail=tail,first_DMA=first,first_section=first_section,sources=sources,early_map=early_map,
                banks=[dict(count=b['count'],seal_ms=ms(b['seal']-origin),release_ms=ms(b['release']-origin))
                       for b in plans['banks557']],
                long_ROM_waits=[dict(index=i,kind=k,address=address,requested_ms=ms(req-origin),
                                     grant_ms=ms(grant-origin),wait_ms=ms(grant-req))
                                for i,(k,address,req,grant,response,mode) in enumerate(reads) if ms(grant-req)>0.25],
                first_DMA_ms=ms(first['clock']-origin),last_ROM_ms=ms(grants[-1][4]-origin),
                checks={k:dict(clock=r['clock'],frame=r['frame'],line=r['line'],ms=ms(r['clock']-origin))
                        for k in ('load','validate181','upload165_entry','final212','reveal','ack') for r in [one(seal,k)]},
                section5_E1_B=sum(e['bytes'] for (h,_,_),e in zip(commands,pushes) if h[1]==5),
                total_SPI_B=sum(e['bytes'] for e in spi))


def display_drift(folder,ref):
    rows=csv_groups(folder/'window.csv')
    delta=0
    changes=[]
    for g in range(905,958):
        frame=one([r for r in rows[g] if r['op']==3],'reveal')['frame']
        diff=frame-ref[g]
        if diff!=delta:
            changes.append(dict(generation=g,cumulative_VB=diff))
        delta=diff
    return changes


def analyze(a):
    cal=Calendar(a.calendar)
    addr=[v for _,h in read(a.plans/'frame954/plans.json') for q in [bytes.fromhex(h)] if q[6]==0 for _,v in lanes(q)]
    guards=read(a.build/'guards.json')
    archive=read(a.reference)
    phases=[]
    modes=('baseline','linear','tables','both','transition','tables-bg')
    for i in (1,2):
        base=a.traces/f'nes-raw624-T-{i}'
        payload=work(base)
        j=read(base/'joint.json')
        reference_frames={g:one([r for r in rows if r['op']==3],'reveal')['frame']
                          for g,rows in csv_groups(base/'window.csv').items() if 905<=g<=957}
        phase={}
        for mode in modes:
            folder=base if mode=='baseline' else a.traces/f'nes-seal625-{mode}-{i}'
            joint=read(folder/'joint.json')
            assert joint['firmware_SHA256']==guards[mode]['firmware']
            assert all(joint[k]==j[k] for k in ('parameters','client_SHA256','vram_DMA_B','ROM_read_allocations'))
            assert work(folder)==payload
            assert all(sha(base/f)==sha(folder/f) for g in range(905,958) for f in (f'frame-{g}.rgb',f'map-{g}.bin'))
            r=measure(folder,cal,addr)
            if mode=='baseline':
                assert r['pins']==archive['phases'][i-1]['T624']['pins']
            r['path955']=trace955(folder)
            if mode in ('tables-bg','baseline'):
                r['grants957']=detail(folder)['grants']
            r['drift_from_T624']=display_drift(folder,reference_frames)
            phase[mode]=r
            b=phase['baseline']
            r['ACK_delta_ms']=ms(r['last_ACK']-b['last_ACK'])
            r['delta_vs_621_ms']=ms(r['last_ACK']-archive['phases'][i-1]['621']['last_ACK'])
            r['structural_guard']=(r['display922']==92 and r['ROM923']['response']<=b['ROM923']['response']
                                    and r['display906']==9 and r['ROM96']==96 and r['wait957']==0
                                    and r['same_blank957'] and r['intervals'][952]==r['intervals'][954]==4
                                    and r['map955']==[192,384])
            r['pass']=r['structural_guard'] and r['intervals'][955]<=4 and r['dense']<=20 and r['ACK_delta_ms']<=0
        d=a.traces/f'nes-seal625-control-{i}'
        trial=a.traces/f'nes-seal625-transition-{i}'
        cutoff=read(d/'control.json')['bypassed_at']
        j_ctrl=read(d/'joint.json')
        assert j_ctrl['firmware_SHA256']==guards['transition']['firmware']
        assert all(j_ctrl[k]==j[k] for k in ('parameters','client_SHA256','vram_DMA_B','ROM_read_allocations'))
        assert work(d)==payload and all(sha(d/f)==sha(base/f) for g in range(905,958)
                                        for f in (f'frame-{g}.rgb',f'map-{g}.bin'))
        prefixes=[[e for e in read(folder/'events.json') if e['clock']<=cutoff] for folder in (trial,d)]
        assert prefixes[0]==prefixes[1] and prefixes[0][-1]['generation']==955
        control=measure(d,cal,addr)
        control['path955']=trace955(d)
        control['bypassed_at']=cutoff
        control['matched_prefix_events']=len(prefixes[0])
        control['transition_minus_control_ms']=ms(phase['transition']['last_ACK']-control['last_ACK'])
        phase['control']=control
        phases.append(phase)
    controls={k:read(a.traces/f'nes-seal625-fixed-{k}/audit.json') for k in ('base','late')}
    assert controls['base']['after']==controls['late']['before']
    r=controls['base']['after']
    assert int(next(x for x in r if x['event']=='ack')['clock'])==phases[1]['baseline']['path955']['checks']['ack']['clock']
    consumer={}
    for mode,prefix in [('transition','nes-seal625'),('tables-bg','nes-seal625-tables-bg')]:
        edges=read(a.traces/f'{prefix}-edges/edges.json')
        assert {r['case'] for r in edges if r['grant']==0}>={'stop','head','both'}
        assert {(r['generation'],r['fault']) for r in edges if 'fault' in r}=={
            (g,f) for g in (906,907) for f in ('missing','duplicate')}
        stops=read(a.traces/f'{prefix}-stop/result.json')+read(a.traces/f'{prefix}-raw-stop/result.json')
        assert len(stops)==12 and all(r['status']==0xe4 for r in stops)
        consumer[mode]=dict(priority=edges,STOP=stops)
    sizes={m:(a.build/m/'src/obj-nes-100/firmware.stm').stat().st_size for m in (*modes[1:],'plan-only')}
    assert max(sizes[m] for m in modes[1:])<=212992<sizes['plan-only']
    result=dict(phases=phases,replays=controls,ARM=guards,consumer=consumer,
                Flash=sizes,Flash_limit=212992,over_budget_SHA256=sha(a.build/'plan-only/src/obj-nes-100/firmware.stm'),
                pass_both={m:all(p[m]['pass'] for p in phases) for m in modes[1:]})
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('build','traces','calendar','plans','reference','out'):
        p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
