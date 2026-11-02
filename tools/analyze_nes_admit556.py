# SPDX-License-Identifier: MIT
"""Partition the same 192-byte packet and compare all four linked schedules."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from analyze_nes_grant555 import ledger, map_admission
from analyze_nes_map553 import map_times
from analyze_nes_phase537 import Calendar, csv_groups, ms, one, read, sha
from analyze_nes_prelude554 import packet_schedule
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare
from verify_nes_trial533 import fpga,timing


def timeline(folder,audit):
    packet=map_admission(folder)
    instructions=list(csv.DictReader((audit/'admission556.csv').open()))
    assert {int(r['index']) for r in instructions}=={packet['index']}
    events=[r for r in read(folder/'events.json') if r['generation']==954]
    entry,enqueue=(one([r for r in events if r.get('offset')==2432],k)['clock'] for k in ('map_packet_enter','map_enqueue'))
    e1,=[r for r in events if r.get('opcode')=='0xe1' and abs(r['clock']-packet['push'])<1]
    assert e1['bytes']==211
    clocks=dict(ARM_packet=entry,ARM_enqueue=enqueue,SPI_start=e1['start'],PUSH=packet['push'],load=packet['load']['clock'])
    for r in instructions:clocks.setdefault(r['event'],int(r['clock']))
    clocks['ack']=packet['ack']['clock']
    assert list(clocks.values())==sorted(clocks.values())
    stages={j:round(clocks[j]-clocks[i]) for i,j in zip(clocks,list(clocks)[1:])}
    return dict(packet=packet,clocks=clocks,stages=stages,
                mark_to_append=clocks['append212']-clocks['mark212'],DMA_to_accepted=clocks['accepted']-clocks['DMA_start'])


def obj_deadline(folder,cal,*,queued=False):
    previous=one([r for r in csv_groups(folder/'window.csv')[953] if r['op']==3],'reveal')['clock']
    target=int(previous*8//cal.period)+4
    cycle=target//8
    grants=[(g+cycle*cal.period,r+cycle*cal.period) for g,r in cal.pairs
            if int((g+cycle*cal.period)*8//cal.period)==target]
    obj=read(folder/'obj-phases.json')['954']
    reads=(obj['rom_service'][-18:] if queued else [r for r in obj['rom_service'] if r[1]>=obj['end_accepted']])
    assert reads[0][1]>=obj['end_accepted']
    assert len(reads)==18 and all(row[0]==1 for row in reads)
    gaps=[b[1]-a[3] for a,b in zip(reads,reads[1:])]
    assert min(gaps)>=0
    latest=float('inf')
    remaining=len(reads)
    for grant,response in reversed(grants):
        if response<=latest:
            remaining-=1
            if not remaining:
                latest=grant
                break
            latest=grant-gaps[remaining-1]
    assert remaining==0
    spi=[dict(op=r['opcode'],start=r['start'],end=r['clock']) for r in read(folder/'events.json')
         if r['generation']==954 and r['event']=='SPI' and abs(r['clock']-reads[0][1])<20000]
    return dict(request=reads[0][1],latest_first_grant=latest,
                margin_clocks=latest-reads[0][1],observed_issue_gaps=gaps,adjacent_SPI=spi,
                missed_reads=sum(int(r[2]*8//cal.period)>target for r in reads))


def analyze(a):
    cal=Calendar(a.traces/'nes-service509-rom03')
    old=read(a.previous)['phases']
    result=[]
    for i in (1,2):
        reference=old[i-1]['map']; base=a.traces/reference['trace_folder']
        variants={}
        for mode in ('base','joint','arm','combined'):
            folder=base if mode=='base' else a.traces/f'nes-admit556-{mode}{i}'
            audit=a.traces/f'nes-admit556-audit-{mode}{i}'
            arm=a.arm if mode in ('arm','combined') else a.old_arm
            client=a.client if mode in ('joint','combined') else a.old_client
            cost=inspect_run(folder,a.plans,cal,base,sha(arm/'obj-nes-100/firmware.stm'),sha(client/'sink165.sfc'),first_bg_limit=3)
            replay=read(audit/'audit.json')
            assert replay['frames']==53 and replay['trace']==cost['pins']['window.csv']
            with (audit/'bitmaps556.csv').open() as f:
                spans=list(csv.DictReader(f))
            units=Counter()
            for s in spans:units[str((int(s['bank']),int(s['section'])))]+=int(s['units'])
            assert len(units)==6
            if mode=='base':
                assert cost['pins']==reference['cost']['pins']
            else:
                assert units==variants['base']['bitmap_units']
            commands=ledger(folder,audit)
            schedule=packet_schedule(folder,cal)
            tail=[r for r in csv_groups(folder/'window.csv')[957] if r['op']==3]
            wait957=sum(r['event']=='wait169' and r['clock']>=one(tail,'final212')['clock'] for r in tail)
            early957=sum(r['push_minus_last_tile_ACK_ms']<0 for r in map_times(folder)['maps'])
            dense=cost['dense_frames']
            later=[g for g,b in cost['BG'].items() if b['relative_window']>reference['cost']['BG'][str(g)]['relative_window']]
            delta=compare(cost,reference['cost'])
            # Compare strict continuous time/last ACK against the direct 555
            # control and require an actual two-phase VBlank win over 554.
            gate=(dense[953]['before_head']+dense[953]['after_head']<=5 and dense[952]['before_head']<=5
                  and not any(cost['waits'].values()) and not wait957 and early957>=2 and not later
                  and schedule['before_head']<=4 and schedule['display_VB']<=5 and cost['dense_VB']<=27
                  and delta['dense_ms']<0 and delta['last_ACK_ms']<0)
            variants[mode]=dict(trace=folder.name,audit=audit.name,cost=cost,packet=timeline(folder,audit),commands954=commands,obj_deadline=obj_deadline(folder,cal),
                schedule954=schedule,bitmap_spans=len(spans),bitmap_units=units,replay=replay,delta=delta,
                wait957=wait957,early957=early957,later_BG=later,gate=gate)
        fixed=a.traces/f'nes-admit556-fixed{i}'
        assert sha(fixed/'input/packets.jsonl')==sha(base/'packets.jsonl')
        trace=csv_groups(fixed/'run/window.csv')
        seal=[r for r in trace[954] if r['op']==3]
        idx=variants['base']['packet']['packet']['index']
        p=[r for r in trace[954] if r['index']==idx]
        variants['joint']['fixed']=dict(audit=read(fixed/'run/audit.json'),accept_line=one(p,'ack')['line'],
            head_to_ack=one(p,'ack')['clock']-one(p,'load')['clock'],
            display_VB=one(seal,'reveal')['frame']-one([r for r in trace[953] if r['op']==3],'reveal')['frame'])
        result.append(variants)
    checks={k:read(a.checks/(k+'.json')) for k in ('crc','guards','credit','menu','window')}
    fw=sha(a.arm/'obj-nes-100/firmware.stm')
    assert fw==checks['crc']['firmware']==checks['guards']['sha']==checks['credit']['sha']==checks['menu']['firmware']==checks['window']['firmware_SHA256']
    checks['priority']=read(a.traces/'nes-admit556-priority/result.json')
    checks['STOP']=read(a.traces/'nes-admit556-stop/result.json')
    checks['direct_mark_cases']={k:read(a.traces/f'nes-admit556-ranges-{k}/cases.json') for k in ('base','candidate')}
    assert all(v==108 for v in checks['direct_mark_cases'].values())
    assert len(checks['priority'])==22 and len(checks['STOP'])==3 and all(r['status']==228 and r['commits']==49 for r in checks['STOP'])
    pins=read(a.board/'inputs535.json')
    assert len(pins)==73 and all(sha(a.board/n)==h for n,h in pins.items())
    changed=[n for n,h in pins.items() if sha(a.old_board/n)!=h]
    assert changed==['sink-program.hex'] and pins[changed[0]]==sha(a.client/changed[0])
    ref555=a.traces/'nes-admit556-board555'
    base_pins=read(ref555/'inputs535.json')
    assert base_pins.keys()==pins.keys() and all(sha(ref555/n)==h for n,h in base_pins.items())
    assert [n for n in base_pins if base_pins[n]!=pins[n]]==['sink-program.hex']
    assert sha(a.old_client/'sink-program.hex')==base_pins['sink-program.hex']
    board={}
    for name,folder in [('candidate',a.board),('MMC551',a.old_board),('555',ref555)]:
        summary,worst,ucp=timing(folder)
        board[name]=dict(cost=fpga(folder),STA=summary,worst=worst,unconstrained=ucp,sof=sha(folder/'output_files/board.sof'))
        for view in ('implementation','nominal'):
            def paths(d):
                with (d/f'{view}-paths204.tsv').open() as f:
                    rows=list(csv.DictReader(f,delimiter='\t'))
                limits={}
                for row in rows:
                    key=tuple(row[k] for k in ('corner','from_clock','to_clock','kind'))
                    limits[key]=min(float(row['slack']),limits.get(key,float('inf')))
                return Counter(tuple(row.values()) for row in rows),limits
            current,limits=paths(folder)
            baseline,old_limits=paths(a.old_board)
            board[name][view]=dict(changed_rows=sum((current-baseline).values()),group_count=len(limits),
                                   group_minima_equal=limits==old_limits)
    return dict(phases=result,gates={m:all(p[m]['gate'] for p in result) for m in ('joint','arm','combined')},
                guards=checks,board=board,changed_inputs=changed,scope='53 captured generations per phase, M4 CPI2, shared SPI/IRQ and periodic boot ROM grants; no hardware FPS.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','plans','client','old-client','arm','old-arm','board','old-board','checks','previous','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
