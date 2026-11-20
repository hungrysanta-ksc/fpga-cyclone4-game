"""Reconcile measured ARM phases, capture margins, display intervals and verified DMA."""
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
from prepare_nes_history888 import BASE, COVERAGE, WORK


def publication(path, cap):
    starts = [e['start'] for e in load(path/'events.json')
              if e.get('opcode')=='0xea' and round(e['clock'])==cap['EA']]
    ea, = starts
    names = ['nes_resident211_commit','nes_resident211_commit_end','commit635','commit635_end',
             'nes_budget210_display','nes_budget210_display_end','nes_plan200_retire']
    labels = ['E0_to_resident','resident_publish','map_history_and_call_setup','palette_oam_history',
              'runtime_display_checks_and_accounting','budget210_display','to_retire','retire_to_EA']
    profile = load(path/'profile888.json')
    marked = [(n,round(clock)) for n,clock,_ in profile if cap['valid_E0']<=clock<=ea]
    assert [n for n,_ in marked]==names,marked
    ticks = [cap['valid_E0']]+[v for _,v in marked]+[round(ea)]
    return dict(zip(labels,[b-a for a,b in zip(ticks,ticks[1:])],strict=True))


def tile_credit(path):
    wire=[e for e in load(path/'events.json') if e['event']=='SPI']
    payloads=packets(path)
    queue=list(zip(payloads,[e for e in wire if e['opcode']=='0xe1'],strict=True))
    def find(header, offset):
        match,=[(i,e) for i,(p,e) in enumerate(queue,1) if p[:2]==header and
                int.from_bytes(p[8:10],'little')==959 and int.from_bytes(p[10:12],'little')==offset]
        return match
    _,previous=find(bytes([4,3]),32)
    head,_=find(bytes([7,1]),416)
    _,following=find(bytes([7,1]),512)
    retired=next(r['clock'] for r in window(path) if r['index']==head and r['event']=='ack')
    polls=[e for e in wire if e['opcode']=='0xe0' and previous['clock']<e['start']<following['start']]
    return dict(previous_end=round(previous['clock']),retired=retired,next_start=round(following['start']),
                E0=[[round(e['start']),int(e['reply'][10:14],16)] for e in polls],
                second_E0_after_retire=round(polls[1]['start']-retired))


def evaluate(temp):
    fw = WORK/'link-credit/src/obj-nes-100/firmware.stm'
    orig_fw = BASE/'link-credit/src/obj-nes-100/firmware.stm'
    client = digest(COVERAGE/'client02/sink165.sfc')
    menu,retire,cold,hist = [load(WORK/n) for n in
                             ('menu.json','retire.json','guards.json','history-guards.json')]
    assert menu['firmware']==retire['ARM']==digest(fw) and cold['client']==client
    assert fw.stat().st_size<=212992 and menu['rows']['normal']['released']
    out=dict(menu=menu,retire=retire,cold_stop=cold,history=hist,firmware=digest(fw),client=client,
             flash_bytes=fw.stat().st_size,scenes={})
    for scene,gen in [('demo',947),('opening',918),('transition',None)]:
        entries=out['scenes'][scene]={}
        for phase in (1,2):
            prefix=f'nes-tile821-{scene}-jointmirror-p{phase}-'
            original=temp/(prefix+'886-static')
            base=load(original/'joint.json')
            tags=['886-static','888-word']
            if gen and phase==2:
                tags+=['888-reference','888-local']
            if gen:
                target=capture(temp/(prefix+'883-shared'),gen)['ready']-240*341*4
            for tag in tags:
                d=temp/(prefix+tag)
                run=load(d/'joint.json')
                assert run['passed'] and run['parameters']==base['parameters'] and run['client_SHA256']==client
                assert run['firmware_SHA256']==digest(fw if tag=='888-word' else orig_fw)
                assert verify_retire_order(d)==base['commits']==run['commits']
                for f in base['frames']:
                    g=f['generation']
                    actual,expected=[(x/f'frame-{g}.rgb').read_bytes() for x in (d,original)]
                    assert len(actual)==len(expected) and actual[7*STRIDE:231*STRIDE]==expected[7*STRIDE:231*STRIDE]
                    assert (d/f'map-{g}.bin').read_bytes()==(original/f'map-{g}.bin').read_bytes()
                if scene=='demo':
                    assert load(d/'ack861.json')['loads']==load(original/'ack861.json')['loads']
                m=metrics(d)
                r=entries[f'{phase}-{tag}']={k:m[k] for k in
                    ('after_two_VBlanks','last_ACK','opening_marks','held_blank_VBlanks')}
                r['final_E0']=arm_ack(d,m['last_ACK'])
                r['E0_transactions']=run['wire_B']['0xe0']//20
                if tag=='888-word':
                    def shows(p):
                        return {e['g']:e['frame'] for e in window(p) if e['event']=='reveal'}
                    new,old=shows(d),shows(original)
                    r['different_publications']=[[g,old[g],n] for g,n in new.items() if n!=old[g]]
                if gen:
                    cap=breakdown(d,gen,target)
                    r['capture']=cap
                    if tag!='886-static':
                        r['E0_to_EA_clocks']=publication(d,cap)
                    if tag=='888-reference':
                        assert load(d/'events.json')==load(original/'events.json') and run['frames']==base['frames']
                    if tag=='888-local':
                        def prefix_spi(p):
                            return [e for e in load(p/'events.json') if e.get('opcode') and round(e['clock'])<=cap['valid_E0']]
                        before=prefix_spi(original)
                        assert before and before==prefix_spi(d)
                        assert cap['valid_E0']==capture(original,gen)['valid_E0']
                        r['identical_prior_SPI']=len(before)
                if scene=='demo':
                    if phase==1:
                        r['959_credit']=tile_credit(d)
                    r['959']={e['event']:[e['frame'],e['line']] for e in window(d) if e['g']==959 and e['op']==3
                              and e['event'] in ('wait169','final_upload212_same_blank212','reveal','ack')}
                    if tag=='888-word':
                        def writes(variant):
                            report=temp/f'nes-mapwait880-consumer-{phase}-{variant}-g959'
                            ack=next(e['clock'] for e in window(temp/(prefix+variant))
                                     if e['g']==959 and e['op']==3 and e['event']=='ack')
                            assert load(report/'summary.json')['final_ACK']['clock']==ack
                            with (report/'idle-vram.csv').open() as f:
                                return [r for r in csv.reader(f) if 24576<=int(r[1])<25344]
                        before,after=[writes(v) for v in ('886-static',tag)]
                        assert len(before)==768
                        r['959_map_bytes']=len(after)
                        r['959_map_matches']=before==after
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(evaluate(a.temp),indent=2)+'\n',encoding='utf8',newline='\n')
