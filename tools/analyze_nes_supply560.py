# SPDX-License-Identifier: MIT
"""Compare OBJ issue order, actual tile contents and displayed frames with MMC558."""
import argparse
import json
from pathlib import Path
from analyze_nes_phase537 import Calendar, csv_groups, ms, one, read, sha
from analyze_nes_map553 import map_times
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare, timeline


def frame952(folder, plans, calendar):
    cpu = csv_groups(folder/'window.csv')
    previous = one([r for r in cpu[951] if r['op']==3], 'reveal')
    def since(clock):
        return round(ms(clock-previous['clock']), 6)
    seal = [r for r in cpu[952] if r['op']==3]
    events = [r for r in read(folder/'events.json') if r['generation']==952]
    phase = read(folder/'obj-phases.json')['952']
    reads = phase['rom_service']
    bg = [r for r in reads if r[0]==0]
    obj = [r for r in reads if r[0]==1]
    assert all(calendar.select(req)==(grant,resp) for _,req,grant,resp in reads)
    records = [bytes.fromhex(h) for _,h in read(plans/'frame952/plans.json')]
    masks = {int.from_bytes(q[2:4],'little'):q[7] for q in records if q[6]==1}
    assert len(masks)==len(phase['obj_plans'])==len(set(r['slot'] for r in phase['obj_plans']))
    rows = []
    long_run = []
    at = 0
    for plan in phase['obj_plans']:
        slot = plan['slot']
        n = 2*masks[slot].bit_count()
        group = obj[at:at+n]
        assert len(group)==n and group[0][1]>=plan['accepted_clock']
        if 39<=slot<=50:
            long_run.extend(group)
        rows.append(dict(slot=slot, reads=n, E9_ms=since(plan['accepted_clock']),
                         request_ms=since(group[0][1]), grant_ms=since(group[0][2]),
                         done_ms=since(group[-1][3])))
        at += n
    assert at==len(obj)
    # Keep the observed inter-read service gaps. Walk backward to find the
    # latest legal first request for all 112 reads in the preceding window.
    assert len(long_run)==112
    gaps = [b[1]-a[3] for a,b in zip(long_run,long_run[1:])]
    assert min(gaps)>=0
    target = int(long_run[0][2]*8//calendar.period)-1
    cycle = (target//8)*calendar.period
    latest = float('inf')
    left = len(long_run)
    for g,r in reversed(calendar.pairs):
        grant,reply = g+cycle,r+cycle
        if int(grant*8//calendar.period)!=target or reply>latest:
            continue
        left-=1
        if not left:
            break
        latest = grant-gaps[left-1]
    assert not left
    deadline = dict(latest_request_ms=since(grant),actual_request_ms=since(long_run[0][1]),
                    required_advance_ms=ms(long_run[0][1]-grant))
    mark = {e:since(one(events,e)['clock']) for e in ('source_begin','planner_enter','bg_map_frozen','end_enter')}
    mark.update({e:since(one(seal,e)['clock']) for e in ('load','final212','reveal','ack')})
    mark['wait169_ms'] = [since(r['clock']) for r in seal if r['event']=='wait169']
    mark['BG_ROM_ms'] = [since(bg[0][2]), since(bg[-1][3])]
    mark['last_OBJ_ACK_ms'] = since(max(r['clock'] for r in cpu[952] if r['op']==7 and r['section']==1 and r['event']=='ack'))
    packets = [json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    bg_ack = max((r for r in cpu[952] if r['op']==7 and r['section']==0 and r['event']=='ack'),key=lambda r:r['index'])
    _, pushed, header, payload = packets[bg_ack['index']-1]
    assert bytes.fromhex(header)[:2]==bytes([7,0]) and len(bytes.fromhex(payload))==48
    mark['BG48_packet_push_ms'] = since(pushed)
    mark['BG48_packet_ACK_ms'] = since(bg_ack['clock'])
    return dict(marks=mark, OBJ_slots=rows, ROM_windows=timeline(folder,calendar)['rom_windows'],long_run_deadline=deadline,
                E9_bytes=[r['bytes'] for r in events if r.get('opcode')=='0xe9'])


def analyze(a):
    cal = Calendar(a.calendar)
    guards = read(a.guards)
    fw = a.arm/'obj-nes-100/firmware.stm'
    assert guards['firmware']==sha(fw)
    menu = read(a.menu)
    assert menu['firmware']==sha(fw) and menu['marker_cases']==4
    root=Path(__file__).resolve().parents[1]
    physical=read(root/'analysis/trial558-verification.json')
    phases = []
    for i in (1,2):
        base = a.traces/f'nes-end557-banks-base{i}'
        trial = a.traces/f'nes-supply560-checked{i}'
        control = read(Path(__file__).resolve().parents[1]/'analysis/end557-verification.json')['phases'][i-1]['banks-base']['cost']
        assert control['pins']['window.csv']==sha(base/'window.csv')
        first = {int(g):v['banks557'][0]['first_check']+92 for g,v in read(trial/'obj-phases.json').items()}
        cost = inspect_run(trial,a.plans,cal,base,sha(fw),sha(a.client/'sink165.sfc'),
                           first_bg_limit=3, first_bg_requests=first)
        audit = read((a.traces/f'nes-supply560-replay{i}')/'audit.json')
        assert audit['frames']==53 and audit['trace']==cost['pins']['window.csv']
        delta = compare(cost, control)
        later = [g for g,r in cost['BG'].items() if r['relative_window']>control['BG'][str(g)]['relative_window']]
        def summary(row):
            return {k:row[k] for k in ('dense_frames','dense_VB','dense_ms','last_ACK','DMA_B','SPI_B','ROM_reads','IRQ','ARM_instructions')}
        candidate = frame952(trial,a.plans,cal)
        assert [r['slot'] for r in candidate['OBJ_slots']]==list(range(39,51))+[27,29,31,34]
        seal957 = [r for r in csv_groups(trial/'window.csv')[957] if r['op']==3]
        waits957 = sum(r['event']=='wait169' and r['clock']>=one(seal957,'final212')['clock'] for r in seal957)
        early957 = sum(r['push_minus_last_tile_ACK_ms']<0 for r in map_times(trial)['maps'])
        def intervals(g):
            f=cost['dense_frames'][g]
            return f['before_head']+f['after_head']
        phases.append(dict(phase=i,base=summary(control),candidate=summary(cost),delta=delta,
                           before=frame952(base,a.plans,cal),after=candidate,replay=audit,pins=cost['pins'],
                           final_waits=cost['waits'],waits957=waits957,early957=early957,later_BG=later,
                           timing_gate=intervals(952)<6 and intervals(953)<=5 and intervals(954)<=5
                           and not any(cost['waits'].values()) and not waits957 and early957>=2
                           and not later and all(v<0 for v in delta.values())))
    return dict(phases=phases,guards=guards,menu=menu,firmware=sha(fw),firmware_bytes=fw.stat().st_size,
                Flash_free_B=physical['Flash_B']+physical['free_Flash_B']-fw.stat().st_size,
                client=sha(a.client/'sink165.sfc'),reused_board=dict(SOF=physical['SOF_SHA256'],
                cost=physical['board'],raw_worst_ns=physical['raw_worst_ns']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','traces','guards','menu','calendar','plans','client','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
