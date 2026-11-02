# SPDX-License-Identifier: MIT
"""Join credits, real ARM issues, calendar grants and 65816 events for frame 952."""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import json
from pathlib import Path
from analyze_nes_history547 import beam
from analyze_nes_phase537 import Calendar,ROOT,csv_groups,ms,one,read,sha
from analyze_nes_seal538 import inspect_run


def timeline(folder,cal):
    cpu=csv_groups(folder/'window.csv')
    obj=read(folder/'obj-phases.json')['952']
    events=read(folder/'events.json')
    e=[r for r in events if r['generation']==952]
    prev=one([r for r in cpu[951] if r['op']==3],'reveal')
    rel=lambda t:round(ms(t-prev['clock']),6)
    reads=obj['rom_service']
    groups=defaultdict(list)
    for kind,req,grant,resp in reads:
        assert cal.select(req)==(grant,resp)
        groups[int(grant*8//cal.period-prev['clock']*8//cal.period)].append((kind,req,grant,resp))
    windows=[]
    for window,group in groups.items():
        period=group[0][2]//cal.period
        legal=[period*cal.period+off for off in cal.starts
               if int((period*cal.period+off)*8//cal.period-prev['clock']*8//cal.period)==window]
        assert legal and legal[0]<=group[0][2]<=group[-1][2]<=legal[-1]
        windows.append(dict(last_legal_grant_ms=rel(legal[-1]),last_request_ms=rel(group[-1][1]),window=window,BG=sum(r[0]==0 for r in group),OBJ=sum(r[0]==1 for r in group),
            first_request_ms=rel(group[0][1]),first_grant_ms=rel(group[0][2]),last_response_ms=rel(group[-1][3]),
            max_request_wait_ms=max(ms(r[2]-r[1]) for r in group)))
    records=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    pushes=[r[1] for r in records]
    acks=sorted((r for rows in cpu.values() for r in rows if r['event']=='ack'),key=lambda r:r['index'])
    assert [r['index'] for r in acks]==list(range(1,len(pushes)+1))
    retired=[r['clock'] for r in acks]
    snapshots=[]
    for r in events:
        if r.get('opcode')!='0xe0':continue
        b=bytes.fromhex(r['reply'])
        sent=int.from_bytes(b[3:5],'big');done=int.from_bytes(b[5:7],'big')
        assert b[1]==0xf7 and sent==bisect_right(pushes,r['start']) and done==bisect_right(retired,r['start'])
        snapshots.append((r['start'],r['clock'],sent,done))
    credits=[]
    for ack in cpu[952]:
        if ack['op']!=7 or ack['event']!='ack':continue
        idx=ack['index'];push=pushes[idx-1]
        obs=next(row for row in snapshots if row[3]>=idx)
        credits.append(dict(section=ack['section'],index=idx,push_ms=rel(push),
            outstanding_at_push=idx-bisect_right(retired,push),SNES_ACK_ms=rel(ack['clock']),
            ARM_observed_ms=rel(obs[1])))
    end=one(e,'end_enter')['clock']
    pending=Counter(sent-done for t,_,sent,done in snapshots if end<=t<obj['end_accepted'])
    # Push arrivals and actual SNES ACKs delimit intervals at every occupancy.
    # E0 only samples those intervals and can lag consumption.
    stop=obj['end_accepted']
    changes=defaultdict(int)
    for t in pushes:
        if end<t<stop:changes[t]+=1
    for t in retired:
        if end<t<stop:changes[t]-=1
    depth=bisect_right(pushes,end)-bisect_right(retired,end)
    at=end
    occupied=Counter()
    for t,change in sorted(changes.items()):
        occupied[depth]+=ms(t-at)
        depth+=change
        assert 0<=depth<=4
        at=t
    occupied[depth]+=ms(stop-at)
    assert abs(sum(occupied.values())-ms(stop-end))<0.000001
    seal=[r for r in cpu[952] if r['op']==3]
    head=one(seal,'load')
    e9=[r for r in e if r.get('opcode')=='0xe9']
    push=next(r for r in e if r.get('packet_opcode')==3)
    cuts=[('previous_display',prev['clock']),('source',one(e,'source_begin')['clock']),
        ('planner',one(e,'planner_enter')['clock']),('first_E9',e9[0]['clock']),
        ('first_BG_grant',reads[0][2]),('END_E9',obj['end_accepted']),
        ('last_OBJ_response',obj['last_obj_rom_response']),('last_OBJ_ACK',next(r['clock'] for r in reversed(cpu[952]) if r['op']==7 and r['section']==1 and r['event']=='ack')),
        ('SEAL_push',push['clock']),('SEAL_head',head['clock'])]
    assert cuts==sorted(cuts,key=lambda c:c[1])
    return dict(cuts_ms={name:rel(t) for name,t in cuts},E9=[dict(bytes=r['bytes'],start_ms=rel(r['start']),accepted_ms=rel(r['clock'])) for r in e9],
        end_call_ms=rel(end),rom_windows=windows,bulk_credit=credits,E0_occupancy_while_END_pending=dict(pending),
        actual_queue_depth_ms_while_END_pending=dict(occupied),
        SEAL_head_line=head['line'],display_to_head_VB=head['frame']-prev['frame'])


def slim(row):
    return dict(dense_VB=row['dense_VB'],dense_ms=row['dense_ms'],last_ACK=row['last_ACK'])


def compare(row,base):
    return dict(dense_VB=row['dense_VB']-base['dense_VB'],dense_ms=row['dense_ms']-base['dense_ms'],
                last_ACK_ms=ms(row['last_ACK']-base['last_ACK']))


def analyze(a):
    cal=Calendar(a.calendar)
    old=read(ROOT/'analysis/receipt548-verification.json')['phases']
    counter=read(ROOT/'analysis/drain543-verification.json')['phases']
    out=[]
    for i in (1,2):
        base=a.traces/f'nes-supply549-base{i}'
        ref=old[i-1]['any']['candidate']
        for name,digest in ref['pins'].items():
            if name!='obj-phases.json':
                assert sha(base/name)==digest,(i,name)
        controls=counter[i-1]['base']
        entry=dict(phase=i,base548=slim(ref),counter_only=slim(controls),base_timeline=timeline(base,cal),
                   instrumented_548_ROM_trace_SHA256=sha(base/'obj-phases.json'),variants={})
        for label in a.variants:
            folder=a.traces/f'nes-supply549-{label}{i}'
            audit=a.traces/f'nes-supply549-{label}-audit{i}'
            proof=read(audit/'audit.json')
            assert proof['frames']==53 and sha(audit/'window.csv')==sha(folder/'window.csv')
            arm=a.builds/{'row':'ARM01','three':'ARM02','suffix':'ARM03'}[label]/'src'
            firmware=sha(arm/'obj-nes-100/firmware.stm')
            measured=inspect_run(folder,a.plans,cal,base,firmware,read(base/'joint.json')['client_SHA256'],first_bg_limit=3)
            relative=compare(measured,ref)
            timing=timeline(folder,cal)
            last=beam(folder)
            later_bg=[g for g,bg in measured['BG'].items()
                      if bg['relative_window']>ref['BG'][str(g)]['relative_window']]
            counter_delta=compare(measured,controls)
            entry['variants'][label]=dict(firmware=firmware,timing=timing,cost=measured,delta548=relative,delta_counter=counter_delta,
                audit=proof,beam957=last,later_first_BG_windows=later_bg,gate=timing['display_to_head_VB']<6 and last['waits']==0 and
                not any(measured['waits'].values()) and all(v<0 for v in (*relative.values(),*counter_delta.values())))
        out.append(entry)
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','calendar','plans','builds','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--variants',nargs='+',choices=['row','three','suffix'],default=['row','three','suffix'])
    a=p.parse_args()
    phases=analyze(a)
    costs={}
    for label,dirname,guards,credit,menu in [
        ('row','ARM01','rowguards','guards','menu'),
        ('three','ARM02','threeguards','threecredit','threemenu'),
        ('suffix','ARM03','suffixguards','suffixcredit','suffixmenu'),
    ]:
        if label not in a.variants:continue
        arm=a.builds/dirname/'src'
        image=arm/'obj-nes-100/firmware.stm'
        proof,queue,recovery=(read(a.builds/(n+'.json')) for n in (guards,credit,menu))
        assert proof['firmware']==queue['sha']==recovery['firmware']==sha(image)
        budget=arm/'nes_budget210.c'
        assert sha(budget)==sha(a.builds.parent/'nes-hardware541/ARM02/src/nes_budget210.c')
        assert 'elapsed>=500 && elapsed<5500' in budget.read_text()
        size=(arm.parent/'size.log').read_text().splitlines()[-1].split()
        costs[label]=dict(firmware=sha(image),flash_B=image.stat().st_size,free_B=212992-image.stat().st_size,
            BSS_B=int(size[2]),budget_source=sha(budget),first_batch_guards=proof['rows'],
            queue_guards=queue['rows'],menu=recovery['rows'],marker_cases=recovery['marker_cases'])
    report=dict(phases=phases,builds=costs,
        all_requested_gates={k:all(p['variants'][k]['gate'] for p in phases) for k in a.variants},
        scope='53 coupled captures, two fixed starts, repeated boot grant calendar; no new physical FPS. '
              'Menu transition runs linked ARM with external I/O hooks. The 548 SNES and board RTL are unchanged.')
    a.out.write_text(json.dumps(report,indent=2)+'\n')
