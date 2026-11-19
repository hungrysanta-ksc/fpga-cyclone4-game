"""Compare actual packet DMA, receipt and display clocks with the 858E control."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map830 import load, packets, window
from analyze_nes_output822 import CLK_MS
from analyze_nes_output852 import measure
from analyze_nes_output857 import section5
from analyze_nes_seal858 import seals, trace
from check_nes_game478 import sha
from prepare_nes_tail859 import ROOT, BASE


def micros(ticks):
    return round(ticks*1000/CLK_MS, 2)


def tail(folder):
    bus = load(folder/'events.json')
    writes = [e for e in bus if e.get('opcode') == '0xe1']
    statuses = [e for e in bus if e.get('opcode') == '0xe0']
    events = window(folder)
    stream = packets(folder)
    seal = next(i for i, b in enumerate(stream) if b[0] == 3 and int.from_bytes(b[8:10],'little') == 964)
    with (folder/'wram859-bus/writes.csv').open() as f:
        writes_wram={(int(i),int(j)):int(c) for i,j,n,c in csv.reader(f)}
    def clocks(rows):
        return [(r['index'],r['event'],r['clock']) for r in rows if r['event'] in ('load','ack','reveal')]
    assert load(folder/'wram859-bus/result.json')['passed'] and clocks(events)==clocks(window(folder/'wram859-bus'))
    result = []
    targets=[i for i,b in enumerate(stream[:seal]) if b[:2]==bytes([2,5]) and
             int.from_bytes(b[8:10],'little')==964 and int.from_bytes(b[10:12],'little')>=1121]
    assert len(targets)==2
    for i in targets:
        b = stream[i]
        assert b[:2] == bytes([2,5])
        marks = {e['event']:e['clock'] for e in events if e['index'] == i+1}
        t = [writes[i]['start'], writes[i]['clock']]
        t.extend([marks['load'],writes_wram[i+1,0],writes_wram[i+1,len(b)-17],marks['ack']])
        nxt = next(e['clock'] for e in events if e['index']==i+2 and e['event']=='load')
        credit = next(e['clock'] for e in statuses if e['clock']>=t[-1] and
                      int.from_bytes(bytes.fromhex(e['reply'])[5:7],'big') >= i+1)
        assert t == sorted(t) and nxt >= t[-1]
        result.append(dict(offset=int.from_bytes(b[10:12],'little'),payload_B=len(b)-16,
            next_opcode=stream[i+1][0],next_section=stream[i+1][1],
            E1_start=t[0],E1_end=t[1],load=t[2],DMA_trigger_PC=marks['tail_dma'],
            WRAM_first_write=t[3],WRAM_last_write=t[4],queue_ACK=t[5],
            next_load=nxt,first_observed_retired_E0=credit,
            E1_us=micros(t[1]-t[0]),queued_us=micros(t[2]-t[1]),
            load_to_first_write_us=micros(t[3]-t[2]),first_to_last_write_us=micros(t[4]-t[3]),
            restored_to_ACK_us=micros(t[5]-t[4]),ACK_to_next_load_us=micros(nxt-t[5]),
            ACK_to_E0_us=micros(credit-t[5])))
    return result


def semantic_seals(folder):
    return {g:(head[:2]+head[4:],span,payload)
            for g,(head,span,payload) in seals(folder)[0].items()}


def compare(temp,clip,phase,tags):
    work=load(temp/('nes-trans850-c0' if clip=='transition' else 'nes-comparison851')/clip/clip/'work.json')
    targets={'demo':(2616,2617),'opening':(703,759),'transition':()}[clip]
    rows={}
    for tag in ['858e', *tags]:
        folder=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}-on'
        metrics,geometry,_=measure(temp,clip,phase,'on',tag,column=True)
        row={k:metrics[k] for k in ('arm','client','display_VBlanks','gaps','final_ACK','verified_pictures','held_blank_VBlanks')}
        row['all_display_clocks']=[r['clock'] for r in window(folder) if r['event']=='reveal']
        row['frames']={w['source_frame']:trace(folder,w['g']) for w in work if w['source_frame'] in targets}
        if clip=='demo':
            bus=[e for e in load(folder/'events.json') if e.get('event')=='SPI' and e['generation']==964]
            row['bus_2617']={op:dict(count=len(items),B=sum(e['bytes'] for e in items))
                for op in ('0xe0','0xe1','0xe8') if (items:=[e for e in bus if e['opcode']==op])}
            raw=[b for b in packets(folder) if b[1]==5 and int.from_bytes(b[8:10],'little')==964 and
                 int.from_bytes(b[10:12],'little')>=1121]
            row['raw_and_tables_2617']=dict(heads=len(raw),wire_B=sum(len(b)+3 for b in raw))
        # Count and verify the sequence of all output commands per generation.
        last={}
        for b in packets(folder):
            g=int.from_bytes(b[8:10],'little')
            seq=int.from_bytes(b[2:4],'little')
            if g in last: assert seq==last[g]+1
            last[g]=seq
        check=(semantic_seals(folder),geometry,section5(folder),load(folder/'joint.json')['parameters'],
               (folder/'startup-clock.txt').read_text().split(),metrics['client'])
        if tag=='858e':
            baseline=check
        else:
            assert check==baseline,(tag,clip,phase)
            if tag=='859ref':
                assert row==rows['858e'],(tag,clip,phase,'instrumentation changed schedule')
            if clip=='demo':
                row['tail']=tail(folder)
            row['last_ACK_delta_us']=micros(row['final_ACK']-rows['858e']['final_ACK'])
        rows[tag]=row
    return rows


def collect(temp, selected):
    tag='859'+selected
    data={}
    for clip in ('demo','opening','transition'):
        tags=(['859ref','859a'] if clip=='demo' else [])+list(dict.fromkeys(['859e',tag]))
        data[clip]={phase:compare(temp,clip,phase,tags) for phase in (1,2)}
    checks={case:load(ROOT/f'{tag}-{case}.json') for case in ('stop','identity','consumer','coverage','table','menu','gap')}
    checks['base']=load(ROOT/f'{tag}-base/result.json')
    checks['layout']=load(ROOT/f'layout-{selected}/result.json')
    assert checks['stop']['no_EA_or_D3'] and checks['identity']['committed_unchanged']
    assert checks['consumer']['restart']['commits']==2 and checks['table']['status']==224 and checks['gap']==dict(commits=1,status=224)
    assert all(v['status']==224 for v in checks['coverage'].values())
    assert all(checks['consumer'][k]['status']==228 for k in ('stop','late-stop'))
    assert checks['menu']['rows']['normal']['released']
    assert checks['base']['safe_return'] and checks['base']['base_restored']
    fw=ROOT/f'link-{selected}/src/obj-nes-100/firmware.stm'
    assert fw.stat().st_size<=212992 and checks['menu']['firmware']==checks['base']['firmware_sha256']==sha(fw)
    assert all(phase[tag]['arm']==sha(fw) for phases in data.values() for phase in phases.values())
    goals={}
    for ph in (1,2):
        demo=data['demo'][ph]
        opening=data['opening'][ph]
        frames=demo[tag]['frames']
        goals[ph]=dict(dense_and_ACK=demo[tag]['display_VBlanks']<demo['858e']['display_VBlanks']
                       and demo[tag]['final_ACK']<demo['858e']['final_ACK'],
                       both_two=all(frames[g]['display']==2 for g in (2616,2617)),
                       seal_earlier_from_previous_reveal=frames[2617]['reveal_to_SEAL_us']<demo['858e']['frames'][2617]['reveal_to_SEAL_us'],
                       opening_all_displays_exact=opening[tag]['all_display_clocks']==opening['858e']['all_display_clocks'],
                       opening_deadlines=all(opening[tag]['frames'][g]['reveal_frame']<=opening['858e']['frames'][g]['reveal_frame']
                                             for g in (703,759)))
    paths={v:ROOT/f'link-{v}/src/obj-nes-100/firmware.stm' for v in 'abdefg'}
    paths['858e']=BASE/'link-c/src/obj-nes-100/firmware.stm'
    links={}
    for v,f in paths.items():
        if not f.exists():
            continue
        symbols=(f.parent/'nes_native_sink165.su').read_text().splitlines()
        stack,= [int(line.split('\t')[1]) for line in symbols if ':nes_sink212_seal\t' in line]
        size=(f.parents[2]/'size.log').read_text().splitlines()[-1].split()
        links[v]=dict(B=f.stat().st_size,free_B=212992-f.stat().st_size,sha256=sha(f),
                      bss_B=int(size[2]),seal_static_stack_B=stack)
    return dict(reference='858e',candidate=tag,scenes=data,guards=checks,links=links,goals=goals,
                client_ROM_free_B=load(BASE/'client-e/build.json')['physical_free_B'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('clip',choices=['demo','opening','transition','all'])
    p.add_argument('tags',nargs='+')
    a=p.parse_args()
    rows=collect(a.temp,a.tags[0]) if a.clip=='all' else {phase:compare(a.temp,a.clip,phase,a.tags) for phase in (1,2)}
    a.out.write_text(json.dumps(rows,indent=2)+'\n')
