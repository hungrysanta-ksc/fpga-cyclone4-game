"""Reconcile the capture edge with queue snapshots and full-run display intervals."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_deadline875 import STRIDE, arm_ack
from analyze_nes_map830 import load, window
from check_nes_mapgate881 import measured_wait
from check_nes_oam882 import capture
from check_nes_retire878 import verify_retire_order
from check_nes_strip869 import digest, metrics


def dense(folder):
    rows=window(folder)
    bus=[r for r in load(folder/'events.json') if r.get('opcode')]
    visible=[r for r in rows if r['event']=='reveal']
    result={}
    for g in (907,908):
        final=next(e['clock'] for e in rows if e['g']==g and e['event']=='ack' and e['op']==3)
        ea=next(e for e in bus if e['generation']==g and e['opcode']=='0xea')
        polls=[e for e in bus if e['generation']==g and e['opcode']=='0xe0' and e['clock']<ea['start']]
        assert bytes.fromhex(polls[-1]['reply'])[7:9]==bytes([1,3])
        result[str(g)]=dict(final_ACK=final, polls=[
            [round(e['start']),round(e['clock']),e['reply']] for e in polls[-3:]],
            ea=round(ea['start']))
    finals={e['g']:e['clock'] for e in rows if e['event']=='ack' and e['op']==3}
    overlaps=[]
    for e in bus:
        if e['opcode']!='0xe0':
            continue
        gen=e['generation']
        final=finals.get(gen)
        if final and e['start']<final<=e['clock']:
            reply=bytes.fromhex(e['reply'])
            # A snapshot before the last retirement still reports a live head.
            if reply[2]&1:
                overlaps.append(gen)
    result['final_ACK_during_stale_E0']=overlaps
    for g in (910,952):
        point = capture(folder,g)
        point['capture_edge'] = point['ready'] - 240*341*4
        point['capture_margin'] = point['capture_edge'] - point['D2']
        result[f'input{g}'] = point
    result['reveal950_952'] = {e['g']:[e['frame'],e['line'],e['clock']] for e in visible if e['g'] in (950,952)}
    result['vblanks']={str(b['g']):b['frame']-a['frame'] for a,b in zip(visible,visible[1:])}
    result['map950']=measured_wait(folder,950)
    result['E0_count']=sum(e['opcode']=='0xe0' for e in bus)
    result['E0_wire_clocks']=round(sum(e['clock']-e['start'] for e in bus if e['opcode']=='0xe0'))
    source=next(e for e in load(folder/'events.json') if e['event']=='source_begin' and e['generation']==963)
    first=next(i for i,e in enumerate(bus) if e['opcode']=='0xd1' and e['input_generation']==963)
    result['963']=dict(ready=round(source['capture_ready']),start=round(source['clock']),
                       transactions=[[e['opcode'],e['bytes'],round(e['start'])] for e in bus[first-5:first+2]],
                       display=[[e['event'],e['frame'],e['line'],e['clock']] for e in rows if e['op']==3
                                and e['g']==963 and e['event'] in ('load','upload165_entry','reveal','ack')])
    result['input909_restore']=[]
    for i,e in enumerate(bus):
        if e['opcode']=='0xd1' and e['input_generation']==909:
            pop=bus[i+1]
            assert pop['opcode']=='0xd2'
            result['input909_restore'].append([e['bytes'],round(e['start']),round(e['clock']),round(pop['start'])])
    return result


def report(temp,tag,clip):
    scene=[]
    for ph in (1,2):
        prefix=f'nes-tile821-{clip}-jointmirror-p{ph}-'
        path=temp/(prefix+tag)
        ref=temp/(prefix+'882-direct')
        new,old=[load(d/'joint.json') for d in (path,ref)]
        assert new['parameters']==old['parameters'] and new['client_SHA256']==old['client_SHA256']
        assert new['commits']==old['commits']==verify_retire_order(path)
        for f in old['frames']:
            g=f['generation']
            a,b=[(d/f'frame-{g}.rgb').read_bytes() for d in (path,ref)]
            assert len(a)==len(b) and a[7*STRIDE:231*STRIDE]==b[7*STRIDE:231*STRIDE]
            assert (path/f'map-{g}.bin').read_bytes()==(ref/f'map-{g}.bin').read_bytes()
        m=metrics(path)
        out={k:m[k] for k in ('after_two_VBlanks','last_ACK','pictures','all_wire_B','opening_marks','held_blank_VBlanks')}
        out['ARM_valid_final_E0']=arm_ack(path,m['last_ACK'])
        out['ARM']=new['firmware_SHA256']
        out['client']=new['client_SHA256']
        if clip=='demo':
            assert load(path/'ack861.json')['loads']==load(ref/'ack861.json')['loads']
            out.update(dense(path))
            for g in (910,952):
                point=out[f'input{g}']
                fixed=capture(temp/(prefix+'881-range'),g)['ready'] - 240*341*4
                point.update(edge_881=fixed, margin_to_881=fixed-point['D2'])
        if clip=='transition':
            out['display']={r['g']:[r['frame'],r['line']] for r in window(path)
                            if r['event']=='reveal' and r['g'] in (941,951,952)}
        scene.append(out)
    return scene


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','probes','out'):
        p.add_argument(name,type=Path)
    args=p.parse_args()
    data={}
    for tag,clips in (('881-range',['demo']),('882-direct',['demo']),
                      ('883-packed',['demo']),('883-shared',['opening','transition','demo']),
                      ('883-ack',['opening','transition','demo'])):
        data[tag]={clip:report(args.temp,tag,clip) for clip in clips}
    data['prior_scenes']={}
    for tag in ('872-final','882-direct'):
        data['prior_scenes'][tag]={}
        for clip in ('opening','transition','demo'):
            rows=[]
            for ph in (1,2):
                m=metrics(args.temp/f'nes-tile821-{clip}-jointmirror-p{ph}-{tag}')
                rows.append({k:m[k] for k in ('after_two_VBlanks','last_ACK','opening_marks')})
            data['prior_scenes'][tag][clip]=rows
    probes=args.probes
    data['receiver']=load(probes/'nes-packed883-shared/receiver.json')
    data['907_same_link_control']=load(probes/'nes-packed883-ack/only907.json')
    data['links']={}
    for name in ('nes-oam882-direct','nes-packed883','nes-packed883-wire','nes-packed883-shared','nes-packed883-ack'):
        fw=probes/name/'link-credit/src/obj-nes-100/firmware.stm'
        data['links'][name]={'flash_B':fw.stat().st_size,'sha256':digest(fw)}
    assert data['receiver']['firmware']==[data['links'][n]['sha256'] for n in data['receiver']['names']]
    assert all(row['ARM']==data['links']['nes-packed883']['sha256'] for row in data['883-packed']['demo'])
    for variant in ('shared','ack'):
        w=probes/('nes-packed883-'+variant)
        results={s:load(w/(s+'.json')) for s in ('input-guards','retire-guards','menu869','begin','scrollguard')}
        fw=data['links'][w.name]['sha256']
        assert fw==results['input-guards']['firmware']==results['retire-guards']['ARM']==results['menu869']['firmware']
        assert results['menu869']['rows']['normal']['released']
        assert all(s['ARM']==fw for s in data['883-'+variant]['demo'])
        data['883-'+variant]['guards']=results
        tag = '883-'+variant
        tests = load(w/'guards.json')
        assert tests['source_tag']==tag and tests['client']==data[tag]['demo'][0]['client']
        data[tag]['consumer_guards']=tests
        for ph,row in enumerate(data[tag]['demo'],1):
            def idle(t):
                with (args.temp/f'nes-mapwait880-consumer-{ph}-{t}/idle-vram.csv').open() as f:
                    return [tuple(map(int,r)) for r in csv.reader(f)]
            reference, candidate=idle('882-direct'),idle(tag)
            assert len(reference)==1536
            row['map950'].update(idle_bytes=len(candidate), same_port_address_value=candidate==reference)
    args.out.write_text(json.dumps(data,indent=2)+'\n')
