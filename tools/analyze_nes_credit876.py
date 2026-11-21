"""Compare the early first input read with final COMMIT and the fixed capture edge."""
import argparse
import json
from pathlib import Path

from analyze_nes_deadline875 import analyze, arm_ack, points
from analyze_nes_map830 import load, packets, window
from check_nes_scroll874 import receipt
from check_nes_strip869 import digest, metrics
from check_nes_game478 import crc


def verified_commits(folder):
    previous={}
    retired={}
    count=0
    for event in load(folder/'events.json'):
        if event['event']=='source_begin' and 'previous_output' in event:
            previous[event['generation']]=event['previous_output']
        if event.get('opcode')=='0xea':
            retired[event['generation']]=event['clock']
        if event.get('opcode')=='0xd3':
            g=event['input_generation']
            assert event['generation']==g
            if g in previous:
                assert retired[previous[g]]<event['start']
            count+=1
    assert count==load(folder/'joint.json')['commits']
    return count


def timeline(folder,edge):
    events=load(folder/'events.json')
    start=next(e for e in events if e['event']=='source_begin' and e['generation']==951)
    inputs=[e for e in events if e.get('input_generation')==951 and e.get('event')=='SPI']
    pops=[e for e in inputs if e['opcode']=='0xd2']
    reads=[e for e in inputs if e['opcode']=='0xd1']
    assert len(reads)==len(pops)
    commit=next(e for e in inputs if e['opcode']=='0xd3')
    retire=next(e for e in events if e.get('opcode')=='0xea' and e['generation']==950)
    assert pops[-2]['clock']<commit['clock']<pops[-1]['clock'] and retire['clock']<commit['start']
    target=points(folder)
    m=metrics(folder)
    previous=receipt(folder,950)
    reveal_ack=next(
        f['ACK_masterclock'] for f in load(folder/'joint.json')['frames'] if f['generation']==950)
    issued=[(b,e) for b,e in zip(packets(folder),[e for e in events if e.get('opcode')=='0xe1'],strict=True)
            if int.from_bytes(b[8:10],'little')==950]
    table=next(e for b,e in reversed(issued) if b[1]==5)
    seal=next(e for b,e in issued if b[0]==3)
    identity=next(b[2:10] for b,e in issued if b[0]==3)
    ack_e0=next(e for e in events if e.get('opcode')=='0xe0' and reveal_ack<=e['clock']<retire['start']
                and bytes.fromhex(e['reply'])[7:19]==b'\x01\x03'+identity+b'\x65\x9a')
    reply=bytes.fromhex(ack_e0['reply'])
    assert reply[1]==0xf7 and reply[2]&2 and reply[3:5]==reply[5:7] and reply[19]==crc(reply[1:19],8,7,0)
    shows={e['g']:e['frame'] for e in window(folder) if e['event']=='reveal'}
    assert reveal_ack<=retire['start']
    return dict(capture951_ready=start['capture_ready'],first_offered=round(start['clock']),
                first_D1_end=round(reads[0]['clock']),second_D1_end=round(reads[1]['clock']),
                blocks=[[e['bytes'],round(e['clock']),round(pop['clock'])] for e,pop in zip(reads,pops,strict=True)],
                first_D2_end=round(pops[0]['clock']),early_blocks=sum(e['clock']<retire['clock'] for e in pops),
                last_table950_end=round(table['clock']),SEAL950_end=round(seal['clock']),
                display950_ACK=reveal_ack,checked_E0_950=round(ack_e0['clock']),
                old_EA=round(retire['clock']),last_data_D2=round(pops[-2]['clock']),
                D3=round(commit['clock']),commit_D2=round(pops[-1]['clock']),
                commit_minus_874_edge=round(pops[-1]['clock']-edge),
                source952_ready=target['capture_ready'],seal952=target['SEAL'],display952=target['show'],
                gap952=target['gap'],gap950=previous['gap'],map950=previous['map_DMA1088'],gap936=shows[936]-shows[935],
                dense60=m['after_two_VBlanks'],ACK=m['last_ACK'],E0=arm_ack(folder,m['last_ACK']))


def report(temp):
    root=Path(__file__).resolve().parents[2]
    variants={'committed':('nes-credit876','876-credit'),'retry':('nes-credit876-retry','876-retry'),
              'pause':('nes-credit876-pause','876-pause')}
    results={}
    for variant,(name,tag) in variants.items():
        work=root/'probes'/name
        assert load(work/'guards.json')['source_tag']==tag
        result=analyze(temp,root,work,tag)
        result['ordered_commits']={f'{clip}-{ph}':verified_commits(temp/f'nes-tile821-{clip}-jointmirror-p{ph}-{tag}')
                                   for clip in ('opening','transition','demo') for ph in (1,2)}
        result['receiver_ownership_guards']=load(work/'ownership-guards.json')
        results[variant]=result
    timing={}
    evidence={}
    for ph in (1,2):
        def path(tag):
            return temp/f'nes-tile821-demo-jointmirror-p{ph}-{tag}'
        edge=points(path('874-drain'))['previous_capture_edge']
        timing[ph]={tag:timeline(path(tag),edge) for tag in ('872-final','874-drain','876-control',*(v[1] for v in variants.values()))}
        for variant,(name,tag) in variants.items():
            t=timing[ph][tag]
            results[variant]['gates'][f'phase{ph}_capture_edge']=t['commit_minus_874_edge']<=0 and t['source952_ready']<timing[ph]['874-drain']['source952_ready']
            results[variant]['gates'][f'phase{ph}_936']=t['gap936']<=timing[ph]['872-final']['gap936']
            results[variant]['passed']=all(results[variant]['gates'].values())
        for name in ('control','retry','pause'):
            records=load(root/'probes'/f'nes-credit876-{name}'/f'ownership-{ph}.json')
            ready=timing[ph]['876-'+name]['capture951_ready']
            evidence[f'{name}-{ph}']=[r for r in records if r['capture_ready']==ready and
                                      (r['clock']>=ready or r['event'] in ('nes_sink212_seal','nes_resident211_prepare'))]
    control=root/'probes/nes-credit876-control/link-credit/src/obj-nes-100/firmware.stm'
    return dict(control=dict(ARM=digest(control),flash_B=control.stat().st_size),
                timelines=timing,owners=evidence,variants=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    args.out.write_text(json.dumps(report(args.temp),indent=2)+'\n')
