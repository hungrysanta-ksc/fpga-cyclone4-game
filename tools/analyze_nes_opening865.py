"""Compare the first opening issue, retire and observed credit at the same packet identity."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_nes_ack861 import observe
from analyze_nes_map830 import load, packets, window
from analyze_nes_output852 import measure
from analyze_nes_output857 import section5
from analyze_nes_raw864 import elapsed
from check_nes_game478 import crc, sha
from prepare_nes_trial802 import PROBES


def prefix(folder):
    payloads=packets(folder)
    n=sum(int.from_bytes(p[8:10],'little')<=910 for p in payloads)
    assert n==101
    bus=load(folder/'events.json')
    issues=[e for e in bus if e.get('opcode')=='0xe1'][:n]
    times={}
    for event in window(folder):
        if 0<event['index']<=n and event['event'] in ('load','ack'):
            times[event['index'],event['event']]=event['clock']
    credit={}
    for e in bus:
        if e.get('opcode')!='0xe0':
            continue
        reply=bytes.fromhex(e['reply'])
        assert reply[1]==0xf7 and reply[-1]==crc(reply[1:19],8,7,0)
        retired=int.from_bytes(reply[5:7],'big')
        # One ARM status response can return multiple slots.
        for i in range(len(credit)+1,min(retired,n)+1):
            credit[i]=e['clock']
        if len(credit)==n:
            break
    result=[]
    for i,(b,e) in enumerate(zip(payloads[:n],issues,strict=True),1):
        assert e['generation']==int.from_bytes(b[8:10],'little')
        clocks=[e['start'],times[i,'load'],times[i,'ack'],credit[i]]
        assert clocks==sorted(clocks)
        result.append(dict(index=i,g=e['generation'],op=b[0],section=b[1],clocks=clocks))
    # On 703 the 99th E1 is the final OBJ. Keep the complete SPI interval
    # after packet 98, including status reads that return the previous tile.
    before_obj=[]
    for e in bus:
        if e['event']!='SPI' or not issues[97]['clock']<=e['start']<issues[98]['start']:
            continue
        before_obj.append({k:e[k] for k in ('opcode','start','clock','reply') if k in e})
    polls=Counter(e['opcode'] for e in bus if e['event']=='SPI')
    return payloads[:n],result,before_obj,{opcode:polls[opcode] for opcode in ('0xe0','0xe1','0xe8')}


def first_change(reference,trial,column):
    for a,b in zip(reference,trial,strict=True):
        diff=b['clocks'][column]-a['clocks'][column]
        if abs(diff)>0.01:  # below one modeled ARM cycle
            return dict(index=b['index'],g=b['g'],op=b['op'],section=b['section'],
                        clocks=[a['clocks'][column],b['clocks'][column]],delta_master=round(diff,3))
    return None


def opening(temp,ph,variant):
    tags=['857ref','865copy','864joined','865'+variant]
    links=['nes-trial855/link','nes-tail864/control','nes-tail864/link','nes-opening865/'+variant]
    result={}
    for tag,linked in zip(tags,links,strict=True):
        d=temp/f'nes-tile821-opening-jointmirror-p{ph}-{tag}-on'
        metrics,geometry,_=measure(temp,'opening',ph,'on',tag,column=True)
        assert metrics['arm']==sha(PROBES/linked/'src/obj-nes-100/firmware.stm')
        payload,data,before_obj,polls=prefix(d)
        reveal=[r for r in window(d) if r['event']=='reveal']
        checks=(geometry,section5(d),metrics['client'],load(d/'joint.json')['parameters'],
                (d/'startup-clock.txt').read_text().split())
        if tag=='857ref':
            base=data
            original=payload
            ref=checks
        else:
            assert checks==ref
        first_order=next((i for i,(a,b) in enumerate(zip(original,payload,strict=True)) if a!=b),len(payload))
        if tag in ('857ref','865copy','864joined'):
            assert first_order==101
        assert ordered_streams(original)==ordered_streams(payload)
        assert len(reveal)==62 and [r['g'] for r in reveal]==list(range(905,967))
        result[tag]=dict(arm=metrics['arm'],intervals=metrics['display_VBlanks'],last_ACK=metrics['final_ACK'],
                         common_ordered_prefix=first_order,first={name:first_change(base[:first_order],data[:first_order],i)
                         for i,name in enumerate(('E1_start','head','retire','E0_return'))},
                         opening_transactions=polls,SPI_before_OBJ99=before_obj,tail=data[-6:],deadlines={str(r['g']-905+698):[r['frame'],r['line']] for r in reveal
                                                  if r['g'] in (910,966)})
        if tag=='865copy':
            copy_stream=data
        elif tag=='864joined':
            result[tag]['first_vs_copy']={name:first_change(copy_stream,data,i) for i,name in
                                          enumerate(('E1_start','head','retire','E0_return'))}
    return result


def ordered_streams(payload):
    groups=defaultdict(list)
    sequence={}
    for p in payload:
        g=int.from_bytes(p[8:10],'little')
        n=int.from_bytes(p[2:4],'little')
        assert n==sequence.get(g,0)
        sequence[g]=n+1
        # Independent streams may interleave when producer/queue timing changes.
        groups[g,p[1],p[0]==7].append(p[:2]+p[4:])
    return groups


def dense(temp,ph,variant):
    arm=PROBES/'nes-opening865'/variant/'src'
    tag='865'+variant+'-on'
    a=observe(temp,855,ph,128,high=True)
    b=observe(temp,855,ph,128,high=True,arm_override=arm,tag_override=tag)
    # 855 is the timing baseline. The unchanged 864 sender is the wire oracle
    # for the two joined packets, which have a different layout from 855.
    joined=temp/f'nes-tile821-demo-jointmirror-p{ph}-861-855-128-high-tail864'
    baseline=temp/f'nes-tile821-demo-jointmirror-p{ph}-861-855-128-high'
    candidate=temp/f'nes-tile821-demo-jointmirror-p{ph}-{tag}'
    assert ordered_streams(packets(joined))==ordered_streams(packets(candidate))
    assert section5(baseline)==section5(candidate)
    assert load(baseline/'joint.json')['parameters']==load(candidate/'joint.json')['parameters']
    assert len(a)==len(b)==60
    for old,new in zip(a,b,strict=True):
        assert all(old[k]==new[k] for k in ('source','work','map','tile','SEAL_payload_B'))
    gaps=[sum(x['gap'] for x in rows) for rows in (a,b)]
    clocks=[rows[-1]['marks'][6] for rows in (a,b)]
    delta=elapsed(clocks[1]-clocks[0])
    return dict(intervals=gaps,ACK_clocks=clocks,ACK_change_ms=delta,
                last_ARM_E0_change_ms=elapsed(b[-1]['marks'][7]-a[-1]['marks'][7]),
                passed=gaps[1]<gaps[0] and delta<0)


def report(temp,variant):
    op={ph:opening(temp,ph,variant) for ph in (1,2)}
    demo={ph:dense(temp,ph,variant) for ph in (1,2)}
    fw=PROBES/'nes-opening865'/variant/'src/obj-nes-100/firmware.stm'
    tag='865'+variant
    assert all(op[ph][tag]['arm']==sha(fw) for ph in (1,2))
    deadlines=all(op[ph][tag]['deadlines'][str(f)]<=op[ph]['857ref']['deadlines'][str(f)]
                  for ph in (1,2) for f in (703,759))
    original=(PROBES/'nes-tail864/link/src/obj-nes-100/firmware.stm').read_bytes()
    header=(PROBES/'nes-opening865/header/src/obj-nes-100/firmware.stm').read_bytes()
    # Build headers may vary; all bytes after the eight-byte prefix match.
    assert original[8:]==header[8:]
    return dict(variant=variant,flash_B=fw.stat().st_size,free_B=212992-fw.stat().st_size,arm_SHA256=sha(fw),
                header_only_same_payload=True,
                opening=op,dense=demo,accept_timing=deadlines and fw.stat().st_size<=212992
                and all(d['passed'] for d in demo.values()))


def collect(temp,variants,guarded):
    controls={}
    cases={}
    for variant in variants:
        r=report(temp,variant)
        for ph,trials in r['opening'].items():
            reference={tag:trials.pop(tag) for tag in ('857ref','865copy','864joined')}
            assert controls.setdefault(ph,reference)==reference
            r['opening'][ph]=trials['865'+variant]
        if variant in guarded:
            checks=load(PROBES/'nes-opening865'/variant/'checks/checked.json')
            assert r['arm_SHA256']==checks['timer']['firmware']==checks['menu']['firmware']
            r['tests']={k:v for k,v in checks.items() if k in ('coverage_bank_bit_cases','linked_coverage','empty_map','empty_offer',
                                                               'gather_patch_counts','receiver','layout/result')}
            r['tests'].update(timer=checks['timer']['passed'],menu=checks['menu']['rows']['normal']['released'],
                              base=checks['base/result']['base_restored'])
            r['transition']={}
            for ph in (1,2):
                old,old_geometry,_=measure(temp,'transition',ph,'on','857ref',column=True)
                new,geometry,_=measure(temp,'transition',ph,'on','865'+variant,column=True)
                assert new['arm']==r['arm_SHA256'] and new['client']==old['client'] and old_geometry==geometry
                r['transition'][ph]={k:[old[k],new[k]] for k in
                                     ('display_VBlanks','verified_pictures','held_blank_VBlanks','final_ACK')}
            r['passed_replay_and_guards']=r['accept_timing'] and all(
                v['display_VBlanks'][1]<=v['display_VBlanks'][0] and
                v['verified_pictures']==[50,50] and v['held_blank_VBlanks']==[16,16]
                for v in r['transition'].values())
        cases[variant]=r
    over={}
    for v in ('empty','cursor','suffix'):
        fw=PROBES/'nes-opening865'/v/'src/obj-nes-100/firmware.stm'
        size=fw.stat().st_size
        assert size>212992
        over[v]=dict(bytes=size,excess=size-212992,sha256=sha(fw))
    return dict(clock_columns=['E1_start','SNES_head','SNES_retire','ARM_E0_end'],opening_controls=controls,
                variants=cases,over_flash=over)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('variants',nargs='+')
    p.add_argument('--guarded',nargs='+',default=[])
    args=p.parse_args()
    args.output.write_text(json.dumps(collect(args.temp,args.variants,args.guarded),indent=2)+'\n',newline='\n')
