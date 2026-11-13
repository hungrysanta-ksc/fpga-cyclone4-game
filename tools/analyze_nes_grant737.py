"""Audit the full map DMA, the progress reply that released the sender, and concurrent E1 wire time."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_nes_prefix736 import audit, compare_paths, csv_groups, ms, packets, read, resources, sha


def transfer_evidence(folder):
    rows=csv_groups(folder/'window.csv')
    heads=packets(folder)
    trace=read(folder/'events.json')
    frames=audit(folder)['frames']
    activated=[]
    for g,issued in heads.items():
        sections=[h[1] for h,_,_ in issued]
        if 4 in sections and 5 in sections and sections.index(5)<sections.index(4):
            activated.append(g)
    result={}
    for g in (952,957):
        origin=next(r['clock'] for r in rows[g-1] if r['event']=='reveal' and r['op']==3)
        def relative(clock):
            return ms(clock-origin)
        loads=[r for r in rows[g] if r['event']=='load']
        acks=[r for r in rows[g] if r['event']=='ack']
        issued=heads[g]
        assert len(issued)==len(loads)==len(acks)
        idx=next(i for i,(h,_,_) in enumerate(issued) if h[1]==2 and int.from_bytes(h[10:12],'little')==3392)
        last=issued[idx][0]
        events=[e for e in trace if e.get('event')=='SPI' and e['generation']==g]
        grants=[]
        for e in events:
            if e['opcode']=='0xe0':
                reply=bytes.fromhex(e['reply'])
                if reply[2]==10 and reply[3:5]==reply[5:7] and reply[8:17]==last[:1]+last[2:10]:
                    assert e['clock']>=acks[idx]['clock']
                    grants.append(relative(e['clock']))
        order=[(h[0],h[1],int.from_bytes(h[10:12],'little'),int.from_bytes(h[14:16],'little')) for h,_,_ in issued]
        long=[d['clock'] for d in frames[g]['prefix_map_DMA'] if d['offset']==2048 and d['bytes']==1536]
        streams=[]
        if long:
            start,=long
            end=next(r['clock'] for r in rows[g] if r['event']=='ppu_last' and r['clock']>start)
            for i,(h,_,push) in enumerate(issued):
                if h[1] not in (1,4,5):
                    continue
                e,=[e for e in events if e['opcode']=='0xe1' and abs(e['clock']-push)<=1]
                overlap=max(0,min(end,push)-max(start,e['start']))
                if overlap:
                    streams.append(dict(section=h[1],offset=int.from_bytes(h[10:12],'little'),
                                        wire_overlap_ms=ms(overlap),push_ms=relative(push),
                                        load_ms=relative(loads[i]['clock'])))
                    assert loads[i]['clock']>=end
            dma=[relative(start),relative(end)]
        else:
            dma=[]
        result[g]=dict(order=order,last_map_ACK_ms=relative(acks[idx]['clock']),verified_map_progress_ms=grants,
                       DMA_ms=dma,E1_during_DMA=streams)
    return dict(prefix_before_OAM_generations=activated,frames=result)


def section_history(folder):
    """Compare canonical section 5 bytes for successive final ACKs on each target."""
    commands=packets(folder)
    cpu=csv_groups(folder/'window.csv')
    last={}
    result={}
    for g,stream in commands.items():
        first=stream[0][0]
        assert first[0]==1 and stream[-1][0][0]==3
        bank=int.from_bytes(first[18:20],'little')
        assert bank in (0,1)
        image=bytearray()
        for h,_,_ in stream:
            if h[1]!=5:
                continue
            assert int.from_bytes(h[10:12],'little')==len(image)
            data=h[16:]
            count=int.from_bytes(h[14:16],'little')
            image.extend(data if not count else data*(count//len(data)))
        assert any(r['op']==3 and r['event']=='ack' and r['value']==1 for r in cpu[g])
        if 951<=g<=957:
            prev,old=last[bank]
            assert prev==g-2 and len(old)==len(image)==1754
            spans={'scroll':(0,21),'padding':(21,1121),'raw':(1121,1505),'tables':(1505,1745),'tail':(1745,1754)}
            result[g]={k:sum(x!=y for x,y in zip(old[a:b],image[a:b])) for k,(a,b) in spans.items()}
        last[bank]=(g,image)
    return result


def analyze(temp,probe,out):
    root=Path(__file__).resolve().parents[1]
    old=read(root/'analysis/prefix736-verification.json')['trials']['b']
    builds={v:resources(probe/v/'src') for v in ('arm01','normal01','arm02','normal02','arm03','normal03')}
    result={}
    for tag,n in [('a','01'),('b','02'),('c','03')]:
        phases={}
        for phase in (1,2):
            folder=temp/f'nes-grant737-{tag}{phase}'
            r=compare_paths(temp,probe,tag,phase,folder,probe/('arm'+n)/'src')
            r['bus']=transfer_evidence(folder)
            r['bus727']=transfer_evidence(temp/f'nes-pair727-a{phase}')
            r['margin_gain_vs736B_ms']={g:v['candidate_last_ACK_margin_ms']-old[str(phase)]['map_deadlines'][str(g)]['candidate_last_ACK_margin_ms'] for g,v in r['map_deadlines'].items()}
            # Compare integer master clocks before converting to a six-interval mean.
            def span(path):
                cpu=csv_groups(path/'window.csv')
                def reveal(g):
                    return next(e['clock'] for e in cpu[g] if e['op']==3 and e['event']=='reveal')
                return reveal(957)-reveal(951)
            r['delta']['mean952_957_ms']=ms(span(folder)-span(temp/f'nes-pair727-a{phase}'))/6
            checks=r['protected']
            checks['952_packet_order']=r['bus']['frames'][952]['order']==r['bus727']['frames'][952]['order']
            r['passed']=all(checks.values()) and all(v['candidate_last_ACK_margin_ms']>=0 for v in r['map_deadlines'].values()) and r['delta']['VBlank']<=0 and all(r['delta'][k]<0 for k in ('mean952_957_ms','dense951_955_ms','last_ACK_ms'))
            for bus in (r['bus'],r['bus727']):
                for details in bus['frames'].values():
                    order=details.pop('order')
                    details['packet_count']=len(order)
                    details['packet_order_SHA256']=hashlib.sha256(json.dumps(order,separators=(',',':')).encode()).hexdigest()
            phases[phase]=r
        result[tag]=phases
    observed=section_history(temp/'nes-pair727-a1')
    assert observed==section_history(temp/'nes-pair727-a2')
    guard_files=sorted(probe.glob('*.json'))
    guards={}
    for tag,n in [('a','01'),('b','02'),('c','03')]:
        for stem in ('credit03','deadline02','gate03','menu03','normal-menu03','normal-admission02','normal-runtime02','ownership03','runtime03'):
            assert probe/(stem+'-'+tag+'.json') in guard_files
        for kind in ('arm','normal'):
            guard=probe/f'order-{kind}{n}.json'
            assert guard in guard_files
            order=read(guard)
            v=builds[kind+n]
            assert order['firmware']==v['firmware'] and len(order['cases'])==16 and len(order['independent_raw'])==5
            ref=resources(probe.parent/'nes-pair727'/(kind+'01')/'src')
            assert v['sections']==ref['sections'] and v['structs']==ref['structs']
    for f in guard_files:
        j=read(f)
        if isinstance(j,dict):
            assert j.get('passed',True)
        guards[f.stem]=sha(f)
    stops={}
    for tag in result:
        f=temp/f'nes-grant737-stop-{tag}'/'result.json'
        cases=read(f)
        assert len(cases)==2 and all(x['generation']==957 and x['commits']==52 and x['status']==228 for x in cases)
        stops[tag]=cases
    selected=[tag for tag,n in [('a','01'),('b','02'),('c','03')] if all(x['passed'] for x in result[tag].values()) and
              all(builds[k+n]['Flash_B']<=212992 for k in ('normal','arm'))]
    out.write_text(json.dumps(dict(stage=737,canonical_section5_changes=observed,trials=result,builds=builds,guards=guards,STOP=stops,selected=selected,
                                   CPU_frames=318,physical_FPS=False,new_RTL=False),indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('temp','probe','out'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    analyze(a.temp,a.probe,a.out)
