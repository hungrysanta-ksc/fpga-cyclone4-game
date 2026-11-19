"""Verify identical SEAL meaning, row work, display RGB and final receipts in each run."""
import argparse
import csv
import json
from pathlib import Path
from collections import Counter

from analyze_nes_map830 import window,load,packets
from analyze_nes_output822 import CLK_MS
from analyze_nes_output852 import measure
from analyze_nes_output857 import section5,missed_edge_us
from check_nes_game478 import sha
from prepare_nes_seal858 import ROOT


def seals(d):
    data={}
    lengths=Counter()
    for p in packets(d):
        if p[0]!=3:
            continue
        g=int.from_bytes(p[8:10],'little')
        n=int.from_bytes(p[12:14],'little')
        payload=p[16:]
        assert len(payload)==n and 44<=n<=168 and not n%4 and g not in data
        cut=n-16
        data[g]=(p[:12],p[14:16],payload[:cut]+bytes(168-n)+payload[cut:])
        lengths[n]+=1
    return data,lengths


def trace(d,g):
    events=window(d)
    r=[e for e in events if e['g']==g and e['op']==3]
    def first(k):return next(e for e in r if e['event']==k)
    seal=first('load')
    tx=[e for e in load(d/'events.json') if e.get('opcode')=='0xe1'][seal['index']-1]
    assert tx['generation']==g and tx['packet_opcode']==3
    prior=next(e for e in events if e['event']=='reveal' and e['g']==g-1)
    clocks={'previous_reveal':prior['clock'],'E1_start':tx['start'],'E1_end':tx['clock']}
    clocks.update({k:first(k)['clock'] for k in ('load','validate181','coverage212','upload165_entry','reveal','ack')})
    waits=[(i,e) for i,e in enumerate(r) if e['event']=='wait169']
    if waits:
        i,w=waits[0]
        resume=next(e for e in r[i+1:] if e['event'].startswith('wait_return') or e['event']=='final_upload212_same_blank212')
        missed=missed_edge_us(d,w,resume)
        with (d/'seal528.csv').open() as f:
            edges={int(row['clock'])-int(row['h']) for row in csv.DictReader(f) if row['line']=='225'}
        edges=[edge for edge in edges if 0<=resume['clock']-edge<1364]
        slack=(round((edges[0]-w['clock'])*1000/CLK_MS,2) if len(edges)==1 and w['line']<225 else None)
        clocks['upload_wait']=w['clock']
    else:
        w=None; missed=None; slack=None
    def us(a,b):return round((clocks[b]-clocks[a])*1000/CLK_MS,2)
    return dict(clocks=clocks,SEAL_E1_B=tx['bytes'],wait_line=w and w['line'],
                missed_edge_us=missed,before_edge_us=slack,display=first('reveal')['frame']-prior['frame'],
                reveal_frame=first('reveal')['frame'],reveal_line=first('reveal')['line'],
                final_gate_lines=[e['line'] for e in r if e['event']=='wait_final516'],
                reveal_to_SEAL_us=us('previous_reveal','load'),
                SEAL_wire_us=us('E1_start','E1_end'),wire_end_to_load_us=us('E1_end','load'),
                semantic_us=us('validate181','coverage212'),coverage_to_upload_us=us('coverage212','upload165_entry'),
                DMA_prep_us=us('upload165_entry','upload_wait') if w else None)


def compare(temp,clip,phase,tags):
    ref='856-855' if clip=='demo' else '857ref'
    fixtures=temp/('nes-trans850-c0' if clip=='transition' else 'nes-comparison851')
    work=load(fixtures/clip/clip/'work.json')
    targets={'opening':(703,759),'demo':(2561,2616,2617),'transition':()}[clip]
    result={}
    for tag in (ref,'857b',*tags):
        d=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}-on'
        metrics,geometry,_=measure(temp,clip,phase,'on',tag,column=True)
        expanded,lengths=seals(d)
        startup=(d/'startup-clock.txt').read_text().split()
        checked=(expanded,geometry,section5(d),load(d/'joint.json')['parameters'],startup)
        if tag==ref:baseline=checked
        else:assert checked==baseline,(tag,clip,phase)
        row={k:metrics[k] for k in ('arm','client','held_blank_VBlanks','verified_pictures','display_VBlanks','final_ACK','gaps')}
        row['widths']=lengths
        row['startup']=list(map(int,startup))
        row['frames']={w['source_frame']:trace(d,w['g']) for w in work if w['source_frame'] in targets}
        result[tag]=row
        if tag not in (ref,'857b'):
            for name in (ref,'857b'):
                row[f'ACK_delta_ms_vs_{name}']=round((row['final_ACK']-result[name]['final_ACK'])/CLK_MS,4)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('tags',nargs='+')
    a=p.parse_args()
    r={s:{n:compare(a.temp,s,n,a.tags) for n in (1,2)} for s in ('demo','opening','transition')}
    result=dict(comparisons=r)
    for tag in a.tags:
        variant=tag[-1]
        new_arm=variant=='f'
        link=ROOT/('link-f' if new_arm else 'link-c')/'src/obj-nes-100/firmware.stm'
        client=ROOT/('client' if variant=='c' else f'client-{variant}')
        menu=load(ROOT/('f-menu.json' if new_arm else 'menu.json'))
        base=load(ROOT/('f-base' if new_arm else 'base')/'result.json')
        digest=sha(link)
        assert menu['firmware']==base['firmware_sha256']==digest
        assert base['safe_return'] and base['base_restored']
        assert link.stat().st_size<=212992
        for scene in r.values():
            for phase in scene.values():
                assert phase[tag]['arm']==digest and phase[tag]['client']==sha(client/'sink165.sfc')
        result.setdefault('links',{})[tag]=dict(flash_B=link.stat().st_size,flash_free_B=212992-link.stat().st_size,
            static_ROM_free_B=load(client/'build.json')['physical_free_B'],menu=menu,base=base)
        demo=[r['demo'][p][tag] for p in (1,2)]
        opening=r['opening'][1]
        result.setdefault('goals',{})[tag]={
            'both_2616_and_2617_two':all(row['frames'][g]['display']==2 for row in demo for g in (2616,2617)),
            'both_dense_sum_and_ack_beat_857B':all(row['display_VBlanks']<r['demo'][p]['857b']['display_VBlanks']
                and row['ACK_delta_ms_vs_857b']<0 for p,row in enumerate(demo,1)),
            'opening_p1_703_759_intervals':all(opening[tag]['frames'][g]['display']<=opening['857ref']['frames'][g]['display']
                for g in (703,759)),
            'opening_p1_703_759_absolute_VBlank':all(opening[tag]['frames'][g]['reveal_frame']<=opening['857ref']['frames'][g]['reveal_frame']
                for g in (703,759))}
        cases=['consumer','coverage','stop','identity']
        if variant in ('e','f'):
            cases.append('table')
        guard={k:load(ROOT/f'{tag}-{k}.json') for k in cases}
        assert all(test['status']==224 for test in guard['coverage'].values())
        assert guard['consumer']['restart']['status']==1 and guard['consumer']['late-stop']['status']==228
        assert all(guard[k]['no_EA_or_D3'] for k in ('stop','identity'))
        if 'table' in guard:
            assert guard['table']['status']==224
        result.setdefault('guards',{})[tag]=guard
    a.out.write_text(json.dumps(result,indent=2)+'\n')
