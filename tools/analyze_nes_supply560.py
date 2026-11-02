# SPDX-License-Identifier: MIT
"""Compare OBJ issue order, actual tile contents and displayed frames with MMC558."""
import argparse
import json
from pathlib import Path
from analyze_nes_phase537 import Calendar, csv_groups, ms, one, read, sha
from analyze_nes_map553 import map_times
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare


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
    at = 0
    for plan in phase['obj_plans']:
        slot = plan['slot']
        n = 2*masks[slot].bit_count()
        group = obj[at:at+n]
        assert len(group)==n and group[0][1]>=plan['accepted_clock']
        rows.append(dict(slot=slot, reads=n, E9_ms=since(plan['accepted_clock']),
                         request_ms=since(group[0][1]), grant_ms=since(group[0][2]),
                         done_ms=since(group[-1][3])))
        at += n
    assert at==len(obj)
    mark = {e:since(one(events,e)['clock']) for e in ('source_begin','planner_enter','bg_map_frozen','end_enter')}
    mark.update({e:since(one(seal,e)['clock']) for e in ('load','final212','reveal','ack')})
    mark['wait169_ms'] = [since(r['clock']) for r in seal if r['event']=='wait169']
    mark['BG_ROM_ms'] = [since(bg[0][2]), since(bg[-1][3])]
    mark['last_OBJ_ACK_ms'] = since(max(r['clock'] for r in cpu[952] if r['op']==7 and r['section']==1 and r['event']=='ack'))
    return dict(marks=mark, OBJ_slots=rows, E9_bytes=[r['bytes'] for r in events if r.get('opcode')=='0xe9'])


def analyze(a):
    cal = Calendar(a.calendar)
    guards = read(a.guards)
    fw = a.arm/'obj-nes-100/firmware.stm'
    assert guards['firmware']==sha(fw)
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
    return dict(phases=phases,guards=guards,firmware=sha(fw),firmware_bytes=fw.stat().st_size,
                Flash_free_B=212992-fw.stat().st_size, client=sha(a.client/'sink165.sfc'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','traces','guards','calendar','plans','client','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
