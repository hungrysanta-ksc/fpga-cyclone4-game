"""Reconcile the 959 wait, physical DMA, following capture and full scene timeline."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_deadline875 import arm_ack
from analyze_nes_map830 import load, packets, window
from analyze_nes_transition850 import STRIDE
from check_nes_oam882 import capture
from check_nes_retire878 import verify_retire_order
from check_nes_strip869 import digest, metrics
from nes_coverage886 import BASE, WORK, replacement


def scene(path, reference):
    phases=window(path)
    actual, old=[load(p/'joint.json') for p in (path,reference)]
    assert actual['passed'] and actual['commits']==old['commits']==verify_retire_order(path)
    for field in ('parameters','firmware_SHA256'):
        assert old[field]==actual[field]
    seals=[b for b in packets(path) if b[0]==3]
    needed=[sum(int.from_bytes(b[i:i+2],'little')==0 for i in range(40,184,2)) for b in seals]
    assert all(len(b)==184 for b in seals)
    for f in old['frames']:
        g=f['generation']
        a,b=[(p/f'frame-{g}.rgb').read_bytes() for p in (path,reference)]
        assert len(a)==len(b) and a[7*STRIDE:231*STRIDE]==b[7*STRIDE:231*STRIDE]
        assert (path/f'map-{g}.bin').read_bytes()==(reference/f'map-{g}.bin').read_bytes()
    m=metrics(path)
    out={k:m[k] for k in ('pictures','after_two_VBlanks','last_ACK','opening_marks','held_blank_VBlanks','all_wire_B')}
    out.update(final_E0=arm_ack(path,m['last_ACK']),empty_words_minmax=[min(needed),max(needed)])
    ref_rows=window(reference)
    def coverage_cost(rows):
        clocks={(r['g'],r['event']):r['clock'] for r in rows if r['op']==3 and
                r['event'] in ('coverage212','upload165_entry')}
        return {g:clocks[g,'upload165_entry']-v for (g,k),v in clocks.items() if k=='coverage212'}
    old_cost=coverage_cost(ref_rows)
    new_cost=coverage_cost(phases)
    savings=[old_cost[g]-v for g,v in new_cost.items()]
    out['coverage_saved_range']=[min(savings),max(savings)]
    def intervals(rows):
        visible=[r for r in rows if r['event']=='reveal']
        return {b['g']:b['frame']-a['frame'] for a,b in zip(visible,visible[1:])}
    old_gaps=intervals(ref_rows)
    out['changed_gaps']=[[g,old_gaps[g],v] for g,v in intervals(phases).items() if old_gaps[g]!=v]
    if 'demo-' not in path.name:
        return out
    assert load(path/'ack861.json')['loads']==load(reference/'ack861.json')['loads']
    visible=[r for r in phases if r['event']=='reveal']
    out['intervals']={str(b['g']):b['frame']-a['frame'] for a,b in zip(visible,visible[1:])}
    out['959']={r['event']:[r['frame'],r['line'],r['clock']] for r in phases if r['g']==959 and r['op']==3 and r['event'] in
                ('load','coverage212','upload165_entry','wait169','wait_return_5781','final212','final_upload212_same_blank212','reveal','ack')}
    out['DMA959']=[[r['frame'],r['line'],r['clock'],r['value']] for r in phases if r['g']==959 and r['event']=='ppu_dma']
    out['DMA950']=[[r['frame'],r['line'],r['value']] for r in phases if r['g']==950 and r['event']=='ppu_dma']
    out['capture961']=capture(path,961)
    reference_capture=capture(reference,961)
    edge=reference_capture['ready']-240*341*4-262*341*4
    out['capture961'].update(target_edge_883=edge,margin=edge-out['capture961']['D2'])
    out['empty_words_per_scene']=needed
    out['959_empty_words']=needed[[int.from_bytes(b[8:10],'little') for b in seals].index(959)]
    return out


def reconcile(temp):
    original=load(WORK/'client02/build.json')
    before=load(BASE/'client02/build.json')
    ref_tag='883-shared'
    result={'rom':{k:original[k] for k in ('body_bytes','physical_free_B','loader_B','encoded_B','prefix_B')},
            'reference_free_B':before['physical_free_B'],'guards':load(WORK/'guards.json')}
    for tag,clips in ((ref_tag,('demo','transition','opening')),('886-static',('demo','transition','opening')),('886-only959',('demo',))):
        result[tag]={}
        for clip in clips:
            rows=[]
            for ph in (1,2):
                prefix=f'nes-tile821-{clip}-jointmirror-p{ph}-'
                d,ref=temp/(prefix+tag),temp/(prefix+ref_tag)
                client=(WORK if tag=='886-static' else BASE)/'client02/sink165.sfc'
                assert load(d/'joint.json')['client_SHA256']==digest(client)
                row=scene(d,ref)
                if tag=='886-only959':
                    a,b=[load(p/'events.json') for p in (d,ref)]
                    edge=row['959']['load'][2]
                    prev=[e for e in b if e.get('opcode') and e['clock']<=edge]
                    assert row['959']['load']==result[ref_tag][clip][ph-1]['959']['load']
                    assert prev and prev==[e for e in a if e.get('opcode') and e['clock']<=edge]
                    row['identical_prior_SPI']=len(prev)
                    target=lambda p:[b for b in packets(p) if int.from_bytes(b[8:10],'little')==959]
                    assert target(d)==target(ref)
                rows.append(row)
            result[tag][clip]=rows
    for ph in (1,2):
        def writes(tag):
            run=temp/f'nes-mapwait880-consumer-{ph}-{tag}-g959'
            assert load(run/'summary.json')['final_ACK']['clock']==result[tag]['demo'][ph-1]['959']['ack'][2]
            with (run/'idle-vram.csv').open() as f:
                return [tuple(map(int,r)) for r in csv.reader(f)]
        reference=writes(ref_tag)
        assert len(reference)==768 and [r[1] for r in reference]==list(range(24576,25344))
        actual=writes('886-static')
        target=[r for r in actual if 24576<=r[1]<25344]
        assert target==reference
        result['886-static']['demo'][ph-1]['idle_DMA959']=dict(bytes=len(target),
                      all_idle_bytes=len(actual),same_source_destination_port_value=reference==target)
    result['MMC872_dense']=[]
    for ph in (1,2):
        baseline=metrics(temp/f'nes-tile821-demo-jointmirror-p{ph}-872-final')
        result['MMC872_dense'].append({key:baseline[key] for key in ('after_two_VBlanks','last_ACK')})
    result['phase2_capture_deadlines']={}
    for clip,g in [('demo',947),('opening',918)]:
        prefix=f'nes-tile821-{clip}-jointmirror-p2-'
        base=capture(temp/(prefix+ref_tag),g)
        candidate=capture(temp/(prefix+'886-static'),g)
        deadline=base['ready']-240*341*4
        result['phase2_capture_deadlines'][clip]={'generation':g,'deadline':deadline,
            'reference':base,'static':candidate,'static_late_clocks':candidate['D2']-deadline}
    result['menu']=load(WORK/'menu.json')
    result['boot']=load(temp/'nes-coverage886-boot'/'result.json')
    assert result['boot']['passed'] and result['menu']['rows']['normal']['released']
    assert result['menu']['firmware']==load(temp/'nes-tile821-demo-jointmirror-p1-886-static/joint.json')['firmware_SHA256']
    orig,_,start,new=replacement()
    assert (WORK/'client02/body.bin').read_bytes()==orig[:start]+new+orig[start+len(new):]
    assert result['guards']['client']==digest(WORK/'client02/sink165.sfc')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(reconcile(a.temp),indent=2)+'\n',encoding='utf8',newline='\n')
