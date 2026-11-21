"""Compare a single substituted OBJ reader, its fixed arrivals, and a cold-booted ROM."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_deadline875 import arm_ack
from analyze_nes_map830 import load, packets, window
from analyze_nes_transition850 import STRIDE
from check_nes_deadline887 import breakdown, capture
from check_nes_retire878 import verify_retire_order
from check_nes_strip869 import digest, metrics
from nes_bulk889 import BASE, WORK


def tile(path):
    wire=[e for e in load(path/'events.json') if e['event']=='SPI']
    queue=list(zip(packets(path),[e for e in wire if e['opcode']=='0xe1'],strict=True))
    def find(op,section,offset):
        match,=[(i,e) for i,(p,e) in enumerate(queue,1) if p[:2]==bytes([op,section])
                and int.from_bytes(p[8:10],'little')==959 and int.from_bytes(p[10:12],'little')==offset]
        return match
    idx,e1=find(7,1,416)
    _,previous=find(4,3,32)
    _,following=find(7,1,512)
    rows=window(path)
    times={e['event']:e['clock'] for e in rows if e['index']==idx and e['event'] in ('load','ack')}
    polls=[dict(start=round(e['start']),retired=int(e['reply'][10:14],16),
                after_return=round(e['start']-times['ack'])) for e in wire
           if e['opcode']=='0xe0' and previous['clock']<e['start']<following['start']]
    seal,=[e for p,e in queue if p[0]==3 and int.from_bytes(p[8:10],'little')==959]
    return dict(index=idx,start=round(e1['start']),**times,polls=polls,
                next_OBJ_start=round(following['start']),SEAL_start=round(seal['start']),
                SEAL_events={e['event']:[e['frame'],e['line'],e['clock']] for e in rows
                             if e['op']==3 and e['g']==959 and e['event'] in ('load','wait169','reveal','ack')})


def fixed(temp,phase,original):
    result=[]
    for local in (0,1):
        p=temp/f'nes-bulk889-tile-p{phase}-{local}'
        with (p/'reader.csv').open() as f:
            r={k:int(v) for k,v in csv.reader(f)}
        rows=window(p)
        if not local:
            assert rows==[e for e in window(original) if e['g']<=959]
        head=tile(original)['index']
        r.update({e['event']:e['clock'] for e in rows if e['index']==head and e['event'] in ('load','ack')})
        result.append(r)
    a,b=result
    assert a['load']==b['load'] and a['bulk194']==b['bulk194']
    return dict(original=a,one_packet=b,entry_saved=a['data']-b['data'],return_saved=a['ack']-b['ack'])


def idle_bytes(temp,phase,tag,expected_ack):
    d=temp/f'nes-mapwait880-consumer-{phase}-{tag}-g959'
    assert load(d/'summary.json')['final_ACK']['clock']==expected_ack
    with (d/'idle-vram.csv').open() as f:
        return [r for r in csv.reader(f) if 24576<=int(r[1])<25344]


def dense_tail(path):
    rows=window(path)
    return {g:[[e['event'],e['frame'],e['line'],e['clock'],e['value']] for e in rows
               if e['g']==g and (e['event']=='ppu_dma' or e['op']==3 and
               e['event'] in ('load','wait169','reveal','ack'))] for g in (965,966)}


def evaluate(temp):
    rom=WORK/'client03'
    fw=BASE/'link-credit/src/obj-nes-100/firmware.stm'
    boot=load(temp/'nes-bulk889-boot/result.json')
    menu=load(WORK/'menu.json')
    assert menu['firmware']==digest(fw) and menu['rows']['normal']['released']
    assert boot['passed'] and {c['ROM'] for c in boot['cases']}=={
        digest(p/'sink165.sfc') for p in (rom,BASE/'client02')}
    out=dict(firmware=menu['firmware'],flash=fw.stat().st_size,consumer=digest(rom/'sink165.sfc'),
             ROM_free=load(rom/'build.json')['physical_free_B'],boot=boot,menu=menu,
             MMC872=load(Path(__file__).resolve().parents[1]/'analysis/trial872-package.json')['final_link_runs'],
             fixed_arrivals={},scenes={})
    for scene,gen in [('demo',947),('opening',918),('transition',None)]:
        data=out['scenes'][scene]={}
        for phase in (1,2):
            prefix=f'nes-tile821-{scene}-jointmirror-p{phase}-'
            original=temp/(prefix+'888-word')
            base=load(original/'joint.json')
            if gen:
                target=capture(temp/(prefix+'883-shared'),gen)['ready']-240*341*4
            if scene=='demo':
                out['fixed_arrivals'][phase]=fixed(temp,phase,original)
            for tag in (['888-word','889-local','889-reader'] if scene=='demo' else ['888-word','889-reader']):
                d=temp/(prefix+tag)
                run=load(d/'joint.json')
                assert run['passed'] and verify_retire_order(d)==run['commits']==base['commits']
                assert run['parameters']==base['parameters'] and run['firmware_SHA256']==out['firmware']
                assert run['client_SHA256']==digest((rom if tag=='889-reader' else BASE/'client02')/'sink165.sfc')
                for frame in base['frames']:
                    g=frame['generation']
                    a,b=[(p/f'frame-{g}.rgb').read_bytes() for p in (original,d)]
                    assert len(a)==len(b) and a[7*STRIDE:231*STRIDE]==b[7*STRIDE:231*STRIDE]
                    assert (original/f'map-{g}.bin').read_bytes()==(d/f'map-{g}.bin').read_bytes()
                m=metrics(d)
                r=data[f'{phase}-{tag}']={k:m[k] for k in
                    ('after_two_VBlanks','last_ACK','opening_marks','held_blank_VBlanks')}
                r['final_E0']=arm_ack(d,m['last_ACK'])
                r['E0_transactions']=run['wire_B']['0xe0']//20
                if tag!='888-word':
                    def reveals(folder):
                        return {e['g']:e['frame'] for e in window(folder) if e['event']=='reveal'}
                    prior,current=reveals(original),reveals(d)
                    r['changed_publications']=[[g,prior[g],v] for g,v in current.items() if prior[g]!=v]
                if gen:
                    r['capture']=breakdown(d,gen,target)
                if scene=='demo':
                    assert load(d/'ack861.json')['loads']==load(original/'ack861.json')['loads']
                    row=r['959']=tile(d)
                    if tag=='889-local':
                        def prefix_spi(p):
                            return [e for e in load(p/'events.json') if e.get('opcode') and e['clock']<=row['load']]
                        assert prefix_spi(d)==prefix_spi(original)
                        assert row['load']==out['fixed_arrivals'][phase]['original']['load']
                    if tag=='889-reader':
                        audit=temp/f'nes-mapwait880-consumer-{phase}-{tag}'
                        ref=temp/f'nes-mapwait880-consumer-{phase}-883-shared'
                        with (audit/'idle-vram.csv').open() as f:
                            count=sum(1 for _ in csv.reader(f))
                        assert count==1536 and (audit/'idle-vram.csv').read_bytes()==(ref/'idle-vram.csv').read_bytes()
                        r['950_idle_bytes']=count
                        before=idle_bytes(temp,phase,'888-word',tile(original)['SEAL_events']['ack'][2])
                        after=idle_bytes(temp,phase,tag,row['SEAL_events']['ack'][2])
                        r['map_idle_bytes']=len(after)
                        r['map_idle_matches']=after==before
                        assert len(after)==768 and r['map_idle_matches']
                    if phase==2 and tag!='889-local':
                        r['965_966']=dense_tail(d)
    guards=load(WORK/'guards.json')
    assert guards['client']==out['consumer'] and len(guards['bad_tiles'])==12
    original=temp/'nes-tile821-demo-jointmirror-p1-889-reader'
    fixture=temp/('nes-tile821-demo-jointmirror-p1-'+guards['source_tag'])
    for name in ('client.sfc','packets.jsonl','capture.lua','joint.json'):
        assert digest(original/name)==digest(fixture/name)
    out['guards']=guards
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(evaluate(a.temp),indent=2)+'\n',encoding='utf8',newline='\n')
