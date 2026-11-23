"""Compare runnable admission schedules at identical tile workload, including public display and ACK."""
import argparse
import json
import re
from pathlib import Path
from analyze_nes_chr951 import logtext
from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage
from analyze_nes_tail961 import milliseconds
from check_nes_blank959 import directory, read, rows, sha, summary
from check_nes_menu533 import check as menu_check
from nes_arm964 import ARM, WORK
from nes_credit965 import BASE,FIRST,BOTH
from nes_writable965 import wire


def clocks(folder):
    events=read(folder/'events.json')
    return dict(input906=round(next(e['start'] for e in events if e.get('input_generation')==906 and e.get('opcode')=='0xd1')),
                E9={g:[round(e['start']) for e in events if e.get('generation')==g and e.get('opcode')=='0xe9']
                    for g in (905,906)},
                seals={g:[round(end) for end,_ in wire(folder,g)] for g in (905,906)},
                reveals={int(r['g']):int(r['clock']) for r in rows(folder/'window.csv') if r['event']=='reveal'})


def measured(folder,g):
    d=folder/f'gen{g}'
    log=d/'mail964.log'
    s=logtext(log)
    assert 'PASS914 trace' in s and 'Errors: 0' in s
    origin=int((d/'origin914.txt').read_text())
    seen=[dict(index=int(i),at=int(k)+origin,payload_B=int(n),plans=int(q),crc=crc)
          for i,k,n,q,crc in re.findall(r'ACCEPT954 batch=(\d+) edge=(\d+) bytes=(\d+) plans=(\d+) crc=([a-f0-9]+)',s)]
    packets=wire(folder,g)
    for row in seen:
        end,hexdata=packets[row['index']]
        data=bytes.fromhex(hexdata)
        assert abs(row['at']-end)<2 and row['payload_B']==len(data)-8
        assert row['plans']==data[3] and row['crc']==data[-4:-2].hex()
    polls,diff=map(int,re.search(r'E8914 compared=(\d+) different=(\d+)',s).groups())
    return dict(log_sha=sha(log),polls=polls,differences=diff,grants=seen)


def analyze(temp,tags):
    root=Path(__file__).resolve().parents[1]
    old=read(root/'analysis/mail964-results.json')
    fw=sha(ARM/'link/src/obj-nes-100/firmware.stm')
    assert old['firmware']==fw and menu_check(ARM/'link/src','955')['rows']['normal']['released']
    recovery=read(ARM/'proof/base/result.json')
    assert recovery['safe_return'] and recovery['base_restored'] and recovery['firmware_sha256']==fw
    report=dict(reference='MMC955',simulated=True,firmware=fw,control_tag=BASE,
                menu_and_base=True,phases={})
    for p in (1,2):
        tag=tags[p-1]
        case=report['phases'][p]=dict(tag=tag)
        pre=directory(temp,p,BASE,'cold')
        first=directory(temp,p,FIRST,'cold')
        both=directory(temp,p,BOTH,'cold')
        final=directory(temp,p,tag,'cold')
        original=clocks(pre)
        a,b=clocks(first),clocks(both)
        c=clocks(final)
        case['first_writable']={}
        for g,control,trial,clock0,clock1 in [(905,pre,first,original,a),(906,first,both,a,b)]:
            r=read(trial/'credit965.json')[str(g)]
            i=r['index']
            proof=measured(trial,g)
            grant,=[x for x in proof['grants'] if x['index']==i]
            assert wire(control,g)[i][1]==r['tx']==wire(trial,g)[i][1]
            case['first_writable'][g]=dict(credit_clock=r['at'],ordinal=i+1,wire_B=len(bytes.fromhex(r['tx'])),
                    baseline_E9=clock0['E9'][g][i],issued=clock1['E9'][g][i],RTL_accepted=grant['at'],
                    baseline_seal=clock0['seals'][g][i],acceptance_gain_ms=milliseconds(clock0['seals'][g][i]-grant['at']),
                    input906_gain_ms=milliseconds(original['input906']-clock1['input906']))
        case['all_responses']={g:measured(final,g) for g in (905,906)}
        for g,proof in case['all_responses'].items():
            polls=sum(e.get('generation')==g and e.get('opcode')=='0xe8' for e in read(final/'events.json'))
            assert proof['polls']==polls and proof['differences']==0
            assert [r['index'] for r in proof['grants']]==list(range(len(wire(final,g))))
            i=case['first_writable'][g]['ordinal']-1
            grant=proof['grants'][i]
            case['first_writable'][g].update(full_schedule_accepted=grant['at'],
                full_schedule_acceptance_gain_ms=milliseconds(original['seals'][g][i]-grant['at']))
        case['attempts']={}
        for n in range(1,int(tag.removeprefix('965wire'))+1):
            ds=directory(temp,p,'965wire'+str(n),'cold')
            diagnostics={}
            for g in (905,906):
                log=ds/f'gen{g}/mail964.log'
                if not log.is_file():
                    continue
                s=logtext(log)
                z=re.search(r'E8914 compared=(\d+) different=(\d+)',s)
                diagnostics[g]=dict(polls=int(z[1]) if z else None,differences=int(z[2]) if z else None,
                                    early=re.findall(r'(?:EARLY965|OPEN965) batch=(\d+) (?:snapshot|edge)=(\d+)',s),
                                    sha256=sha(log))
            case['attempts'][n]=diagnostics
        case['E9_and_display_clocks']={'baseline':original,'feedback':c}
        case['D1_gain_ms']=milliseconds(original['input906']-c['input906'])
        def first_input(d):
            events=read(d/'events.json')
            i=next(i for i,e in enumerate(events) if e.get('input_generation')==906 and e.get('opcode')=='0xd1')
            start=next(e for e in events[:i] if e['generation']==906 and e['event']=='source_begin')
            return dict(capture_ready=start['capture_ready'],source_begin=round(start['clock']),
                        preceding_SPI=[(e['opcode'],e['bytes'],round(e['start']),round(e['clock']))
                                       for e in events[:i] if e['event']=='SPI'][-4:])
        case['before_D1']={'baseline':first_input(pre),'feedback':first_input(final)}
        def display906(d):
            w=[r for r in rows(d/'window.csv') if r['g']=='906' and r['op']=='3']
            result={}
            for name in ('load','ppu_dma','ppu_last','reveal','ack'):
                event=next(r for r in (reversed(w) if name=='ppu_last' else w) if r['event']==name)
                result[name]=[int(event[k]) for k in ('clock','frame','line')]
            return result
        case['display906']={'baseline':display906(pre),'feedback':display906(final)}
        case['later_RTL']={}
        for g in range(907,913):
            d=final if g==912 else final/f'gen{g}'
            log=d/'mail964.log'
            text=logtext(log)
            assert 'PASS914 trace' in text and 'Errors: 0' in text
            polls,different=map(int,re.search(r'E8914 compared=(\d+) different=(\d+)',text).groups())
            case['later_RTL'][g]=dict(polls=polls,different=different,sha256=sha(log))
        for cache in ('cold','warm'):
            folder=directory(temp,p,tag,cache)
            base=directory(temp,p,BASE,cache)
            m,checked=measure(folder,ARM)
            _,expected=measure(base,ARM)
            assert checked==expected
            # Packet order can select a different 1,920B run in the same inactive map.
            # The linked consumer replay has checked the full VRAM map byte for byte.
            metrics=summary(folder,base,map1920_destination=None)
            assert read(folder/'joint.json')['firmware_SHA256']==fw
            literal=directory(temp,p,'965measured',cache)
            files=('events.json','window.csv','packets.jsonl','producer.jsonl','joint.json')
            for name in files:
                assert sha(folder/name)==sha(literal/name),name
            if cache=='warm':
                # All hardware-visible events through 906 are identical to the cold RTL replay.
                lead=lambda d:[e for e in read(d/'events.json') if e.get('generation') in (905,906)]
                assert lead(folder)==lead(final)
            snapshot=m['frames'][912]
            pre_dma=lambda f:coverage([r for r in f['preDMA'] if r[3]==f['VBlank'][3]-1])
            ref=measure(base,ARM)[0]['frames'][912]
            vb=metrics['six'];n=metrics['D2_before_911_reveal'];dma=pre_dma(snapshot)
            ack=metrics['ACK912']
            control=old['cases'][f'{cache}-{p}']
            reference,checked955=measure(directory(temp,p,'955final',cache),WORK)
            extra=checked['params']['driver_extra_us']
            assert abs(extra.pop('0xeb')-extra['0xea'])<1e-6 and checked==checked955
            case[cache]=dict(six=vb,reveals=metrics['reveals'],input_blocks=n,prior_DMA_B=len(dma),
                    exact_prior_addresses=dma.keys()==pre_dma(ref).keys(),ACK912=ack,
                    ACK_gain_vs964_ms=milliseconds(control['ACK912']-ack),
                    ACK_gain_vs961_ms=round(control['ACK_gain_vs961_ms']+milliseconds(control['ACK912']-ack),6),
                    ACK_gain_vs955_replay_ms=milliseconds(reference['final_ACK']-ack),
                    reference955_six=reference['intervals'],
                    same_RGB=metrics['RGB'],VRAM_B=metrics['VRAM_B'],literal_SPI_sha256=sha(literal/'events.json'))
        for name,status in [('bad-seal',224),('stop908',228)]:
            d=final/('guard-'+name)
            r=read(d/'result.json')
            assert r['passed'] and r['commits']==3 and r['last_status']==status
            assert sha(d/'retained.rgb')==sha(final/'frame-907.rgb')
        case['retained_generation_after_STOP_or_bad_SEAL']=907
        if any(r['different'] for r in case['later_RTL'].values()):
            donor=directory(temp,p,'965tail','cold')
            replay=summary(donor,final,map1920_destination=None)
            tail,_=measure(donor,ARM)
            f=tail['frames'][912]
            retained=pre_dma(f).keys()==pre_dma(measure(final,ARM)[0]['frames'][912]).keys()
            stages={}
            for g in range(910,913):
                d=donor if g==912 else donor/f'gen{g}'
                log=d/'mail964.log'
                s=logtext(log)
                assert 'PASS914 trace' in s and 'Errors: 0' in s
                n,k=map(int,re.search(r'E8914 compared=(\d+) different=(\d+)',s).groups())
                stages[g]=dict(polls=n,differences=k,log_sha256=sha(log))
            assert not any(row['differences'] for row in stages.values())
            assert retained and len(pre_dma(f))==496
            assert replay['six']==13 and replay['D2_before_911_reveal']==17
            for name,status in [('bad-seal',224),('stop908',228)]:
                guard=donor/('guard-'+name)
                result=read(guard/'result.json')
                assert result['passed'] and result['last_status']==status and result['commits']==3
                assert sha(guard/'retained.rgb')==sha(donor/'frame-907.rgb')
            case['late_feedback']=dict(samples=read(donor/'tail965.json'),recheck=stages,ACK912=replay['ACK912'],
                six=replay['six'],D2_before_show=replay['D2_before_911_reveal'],prior_DMA_B=len(pre_dma(f)),
                exact_prior_addresses=retained,ACK_gain_vs964_ms=milliseconds(old['cases'][f'cold-{p}']['ACK912']-replay['ACK912']))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('tag')
    p.add_argument('--phase2-tag')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--wire',type=Path,required=True)
    a=p.parse_args()
    from nes_verified965 import capture
    tags=[a.tag,a.phase2_tag or a.tag]
    result=analyze(a.temp,tags)
    raw={p:capture(directory(a.temp,p,tag,'cold')) for p,tag in enumerate(tags,1)}
    encoded=json.dumps(raw,indent=2)
    compact=re.sub(r'\[\s+([0-9][^\[\]{}]*?)\s+\]',lambda m:'['+' '.join(m[1].split())+']',encoded)
    assert json.loads(compact)==json.loads(encoded)
    a.wire.write_bytes((compact+'\n').encode('utf-8'))
    result['wire_record_sha256']=sha(a.wire)
    a.out.write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
