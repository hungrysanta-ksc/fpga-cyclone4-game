"""Check complete dot-zero clips and measure map wire, queue, consumer and reveal time."""
import argparse
import csv
from collections import Counter,defaultdict
import json
from pathlib import Path

from analyze_nes_input848 import CLOCK_MS,stats
from analyze_nes_map830 import load,window
from analyze_nes_transition850 import RGB555,STRIDE
from check_nes_game478 import sha
from prepare_nes_map828 import PROBES


def measure(temp,clip,phase,variant,tag):
    root=temp/('nes-trans850-c0' if clip=='transition' else 'nes-comparison851')
    work=load(root/clip/clip/'work.json')
    baseline=variant=='849'
    label=('850c0-849' if clip=='transition' else '851-849') if baseline else tag+'-'+variant
    folder=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{label}'
    pixels=folder/'first-screen' if baseline and clip!='transition' else folder
    result=load(folder/'joint.json')
    assert result['passed'] and result['last_status']==1
    generations=[w['g'] for w in work]
    assert [f['generation'] for f in result['frames']]==generations
    for w in work:
        actual=(pixels/f"frame-{w['g']}.rgb").read_bytes()[7*STRIDE:231*STRIDE]
        source=w['source_frame']
        original=(temp/f'nes-contiguous848-split02/{source}/frame-{source:04d}.rgb').read_bytes()
        assert actual==original[8*STRIDE:232*STRIDE].translate(RGB555),(clip,phase,variant,source)
    events=load(folder/'events.json')
    spi=[e for e in events if e['event']=='SPI']
    verified=load(root/f'sender-{clip}/verified.json')['frames']
    d1=Counter()
    for e in spi:
        if e['opcode']=='0xd1':
            d1[e['input_generation']]+=e['bytes']
    assert [d1[g] for g in generations]==[v['board_D1_B'] for v in verified]
    e1s=[e for e in spi if e['opcode']=='0xe1']
    eas=[e for e in spi if e['opcode']=='0xea']
    starts=[e for e in spi if e['opcode']=='0xd3']
    assert [e['generation'] for e in eas]==[e['input_generation'] for e in starts]==generations
    assert all(f['ACK_masterclock']<=e['start'] for f,e in zip(result['frames'],eas))
    assert all(e['clock']<=s['start'] for e,s in zip(eas,starts[1:]))
    for serial,g in enumerate(generations,1):
        receipt=bytes.fromhex(next(e['reply'] for e in reversed(spi) if e['opcode']=='0xe0' and e['generation']==g))
        assert receipt[7:9]==bytes((1,3)) and int.from_bytes(receipt[11:15],'little')==serial and int.from_bytes(receipt[15:17],'little')==g
    trace=window(folder)
    times={(r['index'],r['event']):r['clock'] for r in trace if r['event'] in ('load','ack')}
    reveal=[r for r in trace if r['event']=='reveal']
    assert [r['g'] for r in reveal]==generations
    if clip=='transition':
        assert load(folder/'blank-interval.json')['source_frames']==12
        with (folder/'held.csv').open() as f:
            held=[tuple(map(int,r)) for r in csv.reader(f)]
        assert [r[0] for r in held]==list(range(reveal[19]['frame']+1,reveal[20]['frame']))
        assert all((bank,lo,hi)==(1,20,0) and sha(folder/f'held-{vb}.rgb')==sha(pixels/'frame-924.rgb')
                   for vb,clock,bank,lo,hi in held)
    records=[json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    assert len(records)==len(e1s)
    banks={}; totals=Counter(); row_changes=Counter(); columns=defaultdict(list); geometry=[]; costs={}; seqlast=None
    for index,((_,push,hexdata,bulk),e) in enumerate(zip(records,e1s),1):
        b=bytes.fromhex(hexdata);op,section=b[:2]
        serial=int.from_bytes(b[4:8],'little');g=int.from_bytes(b[8:10],'little')
        at,n,span=(int.from_bytes(b[j:j+2],'little') for j in (10,12,14))
        assert n+16==len(b) and len(b)+3==e['bytes'] and abs(push-e['clock'])<=1
        if op==1:
            bank=b[18];assert bank==(serial-1)%2
            image=(folder/f'map-{g}.bin').read_bytes()
        if section==2 and op in (2,4,9):
            extent=n if op==2 else span
            expected=image[at:at+extent]
            if op==9:
                base=int.from_bytes(b[16:20],'little')
                assert bank in banks and base==banks[bank][0]==serial-2 and base>0
                prior=banks[bank][1]
                decoded=bytearray()
                for pos in range(0,extent,64):
                    tail=prior[at+pos+36:at+pos+64]
                    assert tail==bytes(28)
                    start=20+(pos//64)*36
                    decoded.extend(b[start:start+36]+tail)
                assert expected==decoded and n==4+36*(extent//64)
            elif op==4:
                assert b[16:]*(extent//2)==expected
            else:
                assert b[16:]==expected
            if g in generations[2:]:
                geometry.extend((g,row) for row in range(at,at+extent,64))
                if bank in banks:
                    previous=banks[bank][1]
                    for row in range(at,at+extent,64):
                        changed=[j for j in range(row,row+64,2) if image[j:j+2]!=previous[j:j+2]]
                        row_changes[len(changed)]+=1
                        if len(changed)==1:
                            j=changed[0]
                            columns[g].append((row,(j-row)//2,previous[j:j+2]==bytes(2)))
                enter,ack=times[index,'load'],times[index,'ack']
                assert push<=enter<ack
                key=(g,at,extent)
                assert key not in costs
                costs[key]=(op,(e['clock']-e['start']+ack-enter)/CLOCK_MS)
                totals.update(packets=1,ref_packets=int(op==9),E1_B=e['bytes'],expanded_B=extent,
                    wire_ticks=e['clock']-e['start'],queue_ticks=enter-push,consumer_ticks=ack-enter,
                    issue_to_accept_ticks=ack-e['start'])
        if op==3:
            assert seqlast!=serial
            banks[bank]=(serial,image)
            seqlast=serial
    ms={k.removesuffix('_ticks')+'_ms':round(v/CLOCK_MS,3) for k,v in totals.items() if k.endswith('_ticks')}
    gaps=[b['frame']-a['frame'] for a,b in zip(reveal[1:],reveal[2:])]
    intervals=[(b['clock']-a['clock'])/CLOCK_MS for a,b in zip(reveal[1:],reveal[2:])]
    return dict(arm=result['firmware_SHA256'],client=result['client_SHA256'],verified_pictures=len(work),
                held_blank_VBlanks=len(held) if clip=='transition' else None,
                measured_intervals=len(gaps),display_VBlanks=sum(gaps),interval_ms=stats(intervals),
                final_ACK=result['frames'][-1]['ACK_masterclock'],final_EA=round(eas[-1]['clock']),
                changed_words_per_acknowledged_row=dict(row_changes),
                single_word_changes={g:dict(rows=len(v),distinct_columns=len({c for _,c,_ in v}),
                    contiguous=all(b[0]==a[0]+64 for a,b in zip(sorted(v),sorted(v)[1:])),
                    previous_value_zero=sum(zero for _,_,zero in v)) for g,v in columns.items()},
                map={**{k:v for k,v in totals.items() if not k.endswith('_ticks')},**ms},
                gaps=gaps),sorted(geometry),costs


def compare(temp,build,out):
    result={}
    for clip in ('demo','opening','transition'):
        result[clip]={}
        for phase in (1,2):
            runs={};by_packet={};geometry=None
            variants=[('849','849',''),('common','common','852-bank'),('reuse','reuse','852-bank')]
            if clip=='demo':
                variants.append(('dma_common','common','852-dma'))
            variants.append(('dma_reuse','reuse','852-dma'))
            for key,v,tag in variants:
                r,rows,costs=measure(temp,clip,phase,v,tag)
                if geometry is not None:
                    assert geometry==rows,(clip,phase,v)
                geometry=rows
                runs[key]=r
                by_packet[key]=costs
            assert runs['common']['arm']==runs['reuse']['arm'] and runs['common']['client']==runs['reuse']['client']
            assert not runs['common']['map'].get('ref_packets',0)
            assert runs['dma_reuse']['arm']==runs['reuse']['arm']
            if clip=='demo':
                assert runs['dma_common']['client']==runs['dma_reuse']['client'] and not runs['dma_common']['map']['ref_packets']
                assert runs['dma_common']['arm']==runs['dma_reuse']['arm']
            def delta(a,b):
                return dict(VBlank=runs[b]['display_VBlanks']-runs[a]['display_VBlanks'],
                            ACK_ms=round((runs[b]['final_ACK']-runs[a]['final_ACK'])/CLOCK_MS,3))
            pairs=[('849','reuse'),('common','reuse'),('849','dma_reuse')]
            if clip=='demo':pairs.append(('dma_common','dma_reuse'))
            local={}
            for v in ('reuse','dma_reuse'):
                diffs=[ms-by_packet['849'][key][1] for key,(op,ms) in by_packet[v].items()
                       if op==9 and key in by_packet['849']]
                if diffs:
                    local[v]=dict(matched_references=len(diffs),faster_wire_plus_consumer=sum(d<0 for d in diffs),
                                  minimum_delta_ms=round(min(diffs),4),maximum_delta_ms=round(max(diffs),4))
            result[clip][phase]=dict(runs=runs,delta={f'{a}_to_{b}':delta(a,b) for a,b in pairs},match_by_map_range=local)
    probe=PROBES/'nes-output852'
    fw=probe/build/'src/obj-nes-100/firmware.stm'
    assert sha(fw)==runs['reuse']['arm']
    result['resources']=dict(flash_B=fw.stat().st_size,limit_B=212992,
                             client_free_B={v:load(probe/v/'build.json')['physical_free_B'] for v in ('client-board','client-dma')})
    result['guards']={v:load(probe/f'guards-{v}.json') for v in ('bank','dma')}
    result['ARM_faults']={v:load(probe/f'arm-{v}.json') for v in ('stop','identity')}
    out.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();compare(a.temp,'bank',a.out)
