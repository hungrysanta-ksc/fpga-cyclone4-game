# SPDX-License-Identifier: MIT
"""Audit queue snapshots and actual DMA while separating prefix drift from the local intervention."""
import argparse
import json
from pathlib import Path

from analyze_nes_bank621 import Calendar, csv_groups, lanes, ms, read, schedule, sha, work
from analyze_nes_palette622 import detail
from check_nes_game478 import crc


def third_push(folder,r):
    c=[x for x in r['detail']['commands'] if x['section']==3]
    assert [(x['offset'],x['B']) for x in c]==[(0,32),(32,96),(128,232),(360,152)]
    spi=[e for e in read(folder/'events.json') if e['generation']==957 and e['event']=='SPI']
    first,second,third=c[:3]
    # One E0 reply precedes the palette, then E1 advances sent without changing the
    # cached retired counter. SPI clock rounding is <1 master clock at PUSH.
    prior=[e for e in spi if e['opcode']=='0xe0' and e['clock']<=second['issue']][-1]
    reply=bytes.fromhex(prior['reply'])
    assert reply[1]==0xf7 and reply[19]==crc(reply[1:19],8,7,0)
    sent=int.from_bytes(reply[3:5],'big')
    retired=int.from_bytes(reply[5:7],'big')
    add=sum(e['opcode']=='0xe1' and prior['clock']<e['start']<third['issue'] for e in spi)
    e0=[]
    for e in spi:
        if not(second['push']-1<=e['start']<third['issue']) or e['opcode']!='0xe0':continue
        b=bytes.fromhex(e['reply'])
        accepted=int.from_bytes(b[3:5],'big')
        done=int.from_bytes(b[5:7],'big')
        assert b[1]==0xf7 and b[19]==crc(b[1:19],8,7,0) and accepted==(sent+add)&65535
        e0.append(dict(start=e['start'],end=e['clock'],pending=(accepted-done)&65535,
                       ack=b[7:19].hex()))
    origin=r['prev_display']
    return dict(cached_pending=(sent+add-retired)&65535,actual_e0=e0,
                push=[x['push'] for x in c],issue=[x['issue'] for x in c],
                from_display_ms=[ms(x['push']-origin) for x in c],
                prefix_gap_ms=ms(third['push']-second['push']),
                second_ack_to_third_issue_ms=ms(third['issue']-second['accepted']))


def measure(d,cal,addr,ref,joint,payload):
    j=read(d/'joint.json')
    assert all(j[k]==joint[k] for k in ('client_SHA256','parameters','ROM_read_allocations','vram_DMA_B'))
    assert work(d)==payload
    assert all(sha(d/f)==sha(ref/f) for g in range(905,958) for f in (f'frame-{g}.rgb',f'map-{g}.bin'))
    s=schedule(d,cal,addr)
    visible_956,=[x for x in csv_groups(d/'window.csv')[956] if x['event']=='reveal' and x['op']==3]
    r=dict(detail=detail(d),prev_display=s['g957']['clocks']['previous_display'],frame956=visible_956['frame'],intervals=s['intervals'],
           last=s['last_ACK'],display906=s['g906']['display_VB'],dense_VB=s['dense_VB'],dense_ms=s['dense_mean_ms'],
           final_wait957=s['final_wait_957'],map955=[s['first_map_955_B'],s['last_map_955_B']],
           ROM96=s['ROM96_in_first_window'],max_slots=s['max_bulk_banks'],pins=s['pins'],wire_B=s['wire_B'])
    r['third']=third_push(d,r)
    r['from_display956_ms']=ms(r['last']-r['prev_display'])
    return r


def compare(a):
    calendar=Calendar(a.calendar)
    addr=[addr for _,h in read(a.plans/'frame954/plans.json') for q in [bytes.fromhex(h)] if q[6]==0 for _,addr in lanes(q)]
    archive=read(a.reference)
    older=read(a.older)
    guards=read(a.build/'guards.json')
    modes=list(guards['candidates'])
    phases=[]
    for i in (1,2):
        ref=a.traces/f'nes-palette622-after-pack-{i}'
        joint=read(ref/'joint.json')
        payload=work(ref)
        phase={}
        for name in ['A',*modes,'control']:
            d=ref if name=='A' else a.traces/f'nes-credit623-{name}-{i}'
            r=measure(d,calendar,addr,ref,joint,payload)
            if name=='A':
                assert r['pins']==archive['phases'][i-1]['after-pack']['pins']
            else:
                mode='small-snapshots' if name=='control' else name
                image=a.build/mode/'src/obj-nes-100/firmware.stm'
                assert read(d/'joint.json')['firmware_SHA256']==guards['candidates'][mode]['arm']==sha(image)
            phase[name]=r
            base=phase['A']
            r['delta_A_ms']=ms(r['last']-base['last'])
            r['delta_619_ms']=ms(r['last']-older['phases'][i-1]['reference']['last_ACK'])
            r['delta_621_ms']=ms(r['last']-older['phases'][i-1]['trial']['last_ACK'])
            r['delta_display956_ms']=ms(r['prev_display']-base['prev_display'])
            r['prefix_delta_ms']=[ms(v-u) for u,v in zip(base['third']['push'][:2],r['third']['push'][:2])]
            r['prefix_exact']=r['third']['push'][:2]==base['third']['push'][:2] and r['prev_display']==base['prev_display']
            r['delta_display956_VB']=r['frame956']-base['frame956']
            r['local_gap_delta_ms']=r['third']['prefix_gap_ms']-base['third']['prefix_gap_ms']
            r['guards_ok']=(r['display906']==9 and r['intervals'][952]==r['intervals'][954]==4 and r['ROM96']==96
                            and r['map955'][0]>=192 and r['map955'][1]==384 and r['final_wait957']==0)
            r['timing_gate']=bool(r['guards_ok'] and r['detail']['same_VBlank']
                                  and max(r['delta_A_ms'],r['delta_619_ms'],r['delta_621_ms'])<0)
        actual,control=phase['small-snapshots'],phase['control']
        assert actual['prev_display']==control['prev_display'] and actual['third']['push'][:2]==control['third']['push'][:2]
        cutoff=control['third']['push'][1]
        traces=[a.traces/f'nes-credit623-{n}-{i}' for n in ('small-snapshots','control')]
        prefixes=[[e for e in read(d/'events.json') if e['clock']<=cutoff] for d in traces]
        assert prefixes[0]==prefixes[1]
        cuts=read(traces[1]/'control.json')['bypassed_at']
        assert len(cuts) in (0,4) and len(actual['third']['actual_e0'])>=len(cuts)
        phase['isolation']=dict(bypassed=len(cuts),matched_events=len(prefixes[0]),cutoff=cutoff,
                                delta_ACK_ms=ms(actual['last']-control['last']))
        displays=[csv_groups(f/'window.csv') for f in (ref,traces[0])]
        events=[read(f/'events.json') for f in (ref,traces[0])]
        drift=[]
        previous_delta=0
        for gen in range(905,958):
            pair=[next(r for r in rows[gen] if r['event']=='reveal' and r['op']==3) for rows in displays]
            delta=pair[1]['frame']-pair[0]['frame']
            if delta!=previous_delta:
                drift.append(dict(generation=gen,delta_VB=delta,delta_ms=ms(pair[1]['clock']-pair[0]['clock']),
                                  E0_counts=[sum(e.get('opcode')=='0xe0' and e['generation']==gen
                                                 for e in stream) for stream in events]))
            previous_delta=delta
        phase['isolation']['T_vs_A_display_drift']=drift
        banks=[read(f/'obj-phases.json') for f in (ref,traces[0])]
        first_loss={}
        for gen in (921,922,923):
            checkpoints=[]
            for stream,rows,bank in zip(events,displays,banks):
                cpu=[r for r in rows[gen] if r['op']==3]
                clocks={k:next(e['clock'] for e in stream if e['generation']==gen and e['event']==k)
                        for k in ('output_enter531','output_return531')}
                clocks.update({k:next(r['clock'] for r in cpu if r['event']==k)
                               for k in ('load','validate181','final212','reveal','ack')})
                clocks['first_ROM_supply']=bank[str(gen)]['cache611'][0][3]
                checkpoints.append(clocks)
            first_loss[gen]={k:ms(checkpoints[1][k]-v) for k,v in checkpoints[0].items()}
        phase['isolation']['T_minus_A_ms']=first_loss
        phases.append(phase)
    edge=read(a.traces/'nes-credit623-edges/edges.json')
    stop=read(a.traces/'nes-credit623-stop/result.json')
    assert {r['case'] for r in edge if r['grant']==0}>={'stop','head','both'}
    assert {(r['generation'],r['fault']) for r in edge if 'fault' in r}=={(g,f) for g in (906,907) for f in ('missing','duplicate')}
    assert {(r['generation'],r['boundary'],r['status']) for r in stop}=={(g,k,0xe4) for g in (906,907) for k in ('budget538','final212')}
    sizes={d.name:(d/'src/obj-nes-100/firmware.stm').stat().st_size for d in a.build.iterdir() if d.is_dir() and (d/'size.log').exists()}
    assert all((sizes[n]<=212992)==(n in modes) for n in sizes)
    replays=[read(a.traces/f'nes-credit623-gap-{i}/audit.json') for i in (1,2)]
    for replay,phase in zip(replays,phases):
        assert replay['baseline']['ACK']==phase['A']['last']
        for key,name in [('source_gap','A'),('measured_gap','small-snapshots')]:
            pushes=phase[name]['third']['push']
            assert replay[key]==pushes[2]-pushes[1]
    result=dict(phases=phases,A_prefix_replays=replays,pass_both={n:all(p[n]['timing_gate'] for p in phases) for n in modes},
                pass_with_A_prefix={n:all(p[n]['timing_gate'] and p[n]['prefix_exact'] for p in phases) for n in modes},Flash_B=sizes,
                ARM_guards=guards,priority=edge,STOP=stop)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','plans','calendar','build','reference','older','out'):
        p.add_argument('--'+name,type=Path,required=True)
    compare(p.parse_args())
