"""Budget a shared OBJ header against the 912 two-bank and two-credit deadlines."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from check_nes_plan975 import directory
from nes_budget1005 import earliest, schedule
from test_nes_banks557 import MASTER

SPI = 2625000
ROOT = Path(__file__).resolve().parents[1]


def wire(size):
    return int(size * 8 * MASTER // SPI)


def patterns(first, last=38):
    """All non-overlapping adjacent OBJ pairs, including no pairing."""
    if first > last:
        yield ()
        return
    yield from patterns(first + 1, last)
    if first < last:
        for rest in patterns(first + 2, last):
            yield (first,) + rest


def read_trace(temp, phase, data):
    control = temp / f'nes-credit1004-control-p{phase}'
    with (control/'window.csv').open() as f:
        times = {}
        for row in csv.DictReader(f):
            if row['g'] == '912':
                events = times.setdefault(int(row['index']), {})
                events[row['event']] = int(row['clock'])
                if row['event'] == 'consume920':
                    events['consumed_token'] = int(row['value'])
    starts = [list(map(int, l.split())) for l in (control/'starts.txt').read_text().splitlines()]
    begin = data['jobs'][0]['index']
    order = [begin] + [r[0] for r in starts]
    assert sorted(order) == [j['index'] for j in data['jobs']]
    trace = {idx: times[begin + n] for n, idx in enumerate(order)}
    for job in data['jobs']:
        if 'token' in job:
            r = trace[job['index']]
            assert r['consumed_token'] == job['token']
            assert r['load'] < r['bulk194920'] < r['first_read920'] < r['consume920'] < r['ack']
    return order, trace, [list(map(int, l.split())) for l in (control/'busy.txt').read_text().splitlines()]


def groups(jobs, pairs):
    by_token = {j['token']: j for j in jobs if 'token' in j}
    grouped = {}
    for j in jobs:
        token = j.get('token', 0)
        if token in pairs:
            second = by_token[token+1]
            assert all(x['op'] == 7 and x['section'] == 1 and x['wire_B'] == 23 for x in (j, second))
            grouped[j['index']] = (j, second)
        elif token-1 not in pairs:
            grouped[j['index']] = (j,)
    assert sum(map(len, grouped.values())) == len(jobs)
    return grouped


def budget(data, trace, groups_by_id, *, section_wire=100, section_cpu=100, tile_advance=0):
    """Free E0/E8 and producer overlap, ideal wire, generous header removal."""
    work = {j['index']: j for j in data['service']['work']}
    packets = list(groups_by_id.values())
    queues = [[p for p in packets[1:-1] if ('tile' if p[0]['op']==7 else p[0]['section'])==kind]
              for kind in ('tile', 3, 4, 5)]

    def step(times, packet):
        bus, older, receiver = times
        first, last = packet[0]['index'], packet[-1]['index']
        cost = sum(work[j['index']]['floor'] for j in packet)
        if first != last:
            # Give back the entire observed intervals, including their stalls.
            cost -= trace[first]['ack'] - trace[first]['consume920']
            cost -= trace[last]['bulk194920'] - trace[last]['load']
        assert cost > 0
        release = max(work[j['index']]['independent_release'] for j in packet)
        if packet[0]['op'] == 7:
            release -= tile_advance
        size = packet[0]['wire_B'] if first == last else 31
        if packet[0]['section'] == 5 and packet[0]['offset'] >= 1121:
            # Sensitivity only. Keep the 19-byte transaction/header per packet.
            size = 19 + (size - 19) * section_wire // 100
            cost = cost * section_cpu // 100
        arrived = max(max(bus, release) + wire(size), older)
        return arrived, receiver, max(arrived, receiver) + cost

    return schedule(queues, packets[0], packets[-1], step) - data['vblank46_start']


def charged(data, order, trace, groups_by_id, busy, poll):
    """Fixed control order, actual service spans, physical returns and polled credit."""
    def reserve(at, duration):
        for start, end in busy:
            if end <= at:
                continue
            if at + duration <= start:
                break
            at = end
        return at

    clock = data['jobs'][0]['issue']
    receiver = 0
    completions = []
    confirmed = 0
    returns = {}
    polls = 0
    queries = 0
    wire_bytes = 0
    head_wait = []
    section5 = 0
    for idx in order:
        if idx not in groups_by_id:
            continue
        packet = groups_by_id[idx]
        j = packet[0]
        tr = trace[idx]
        while len(completions) - confirmed >= 2:
            start = reserve(clock, poll)
            confirmed = sum(t <= start for t in completions)
            polls += 1
            clock = start + poll
        if 'token' in j:
            def ready(tile):
                token = tile['token']
                return max(tile['producer'], returns[token-2] + tile['fill_after_previous_return']
                           if token >= 33 else 0)
            release = max(map(ready, packet))
            if len(packet) == 2:
                head_wait.append(max(0, release-max(clock,ready(j))))
            query = j['e8_cost'] + (wire(8) + 1 if len(packet)==2 else 0)
            queries += 1
        else:
            release = j['source']
            query = 0
        # One transaction setup per E1/E8. Round added serialized bits up.
        extra = wire(8) + 1 if len(packet)==2 else 0
        issue = reserve(max(clock,release), query+j['duration']+extra)
        clock = issue + query+j['duration']+extra
        wire_bytes += j['wire_B'] + (8 if len(packet)==2 else 0)
        if j['section'] == 5:
            section5 += j['wire_B']
        load = max(clock, receiver)
        if 'token' in j:
            returns[j['token']] = load + tr['consume920'] - tr['load']
        if len(packet)==2:
            peer = packet[1]
            tail = trace[peer['index']]
            returns[peer['token']] = returns[j['token']] + tail['consume920'] - tail['bulk194920']
            receiver = returns[peer['token']] + tail['ack'] - tail['consume920']
        else:
            end = 'group1002' if j['op']==3 else 'ack'
            receiver = load + tr[end] - tr['load']
        completions.append(receiver)
    assert sorted(returns)==list(range(31,39)) and section5==540
    return dict(group_late_clocks=receiver-data['vblank46_start'], E0=polls,E8=queries,
                E1_bytes=wire_bytes, section5_E1_bytes=section5, wait_peer_clocks=head_wait)


def inspect(temp, phase, data, control):
    order, trace, busy = read_trace(temp, phase, data)
    jobs = data['jobs']
    obj = [j for j in jobs if j['section']==1 and j['op']==7]
    assert [j['token'] for j in obj] == list(range(32,39))
    gaps = [b['e8_start']-a['physical_return'] for a,b in zip(obj,obj[1:])]
    assert min(gaps) >= 0
    scenarios = []
    actual = control['runs']['control']
    poll = actual['E0_duration']
    for pairs in patterns(32):
        packets = groups(jobs,pairs)
        lower = budget(data,trace,packets)
        model = charged(data,order,trace,packets,busy,poll)
        scenarios.append(dict(pairs=pairs,upload_late_clocks=lower,**model))
    assert len(scenarios)==21 and scenarios[0]['upload_late_clocks']==earliest(data,1000)-data['vblank46_start']
    best = min(scenarios,key=lambda item:item['upload_late_clocks'])
    packets = groups(jobs,best['pairs'])
    sensitivity = {f'wire{w}_cpu{c}':budget(data,trace,packets,section_wire=w,section_cpu=c)
                   for w,c in ((100,100),(50,100),(0,100),(100,50),(50,50),(0,0))}
    offer = {}
    for mode, queue in [('stock',groups(jobs,())),('paired',packets)]:
        lo, hi = 0, 48000
        end = budget(data,trace,queue,tile_advance=hi)
        threshold = None
        if end < 0:
            while hi-lo > 1:
                mid = (lo+hi)//2
                if budget(data,trace,queue,tile_advance=mid) < 0:
                    hi = mid
                else:
                    lo = mid
            threshold = hi
        offer[mode] = dict(advance_for_upload_before_VB46=threshold,late_at_48000=end)
    path = directory(temp,phase,'978returned','cold')/'events.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==data['protected']['events_SHA256']
    events = json.loads(path.read_text())
    enter, = [e['clock'] for e in events if e.get('generation')==912 and e['event']=='planner_enter']
    first = next(e for e in events if e.get('generation')==912 and e.get('opcode')=='0xe9')
    intervals = sorted((max(enter,e['start']),min(first['start'],e['clock'])) for e in events
                       if 'start' in e and 'opcode' in e and e['start']<first['start'] and e['clock']>enter)
    assert all(a>=last for (_,last),(a,_) in zip(intervals,intervals[1:]))
    occupied = sum(end-start for start,end in intervals)
    plan = dict(planner=math.floor(enter),first_E9=math.floor(first['start']),bytes=first['bytes'],
                accepted=math.floor(first['clock']),occupied_before_issue=round(occupied),
                unsent_bus_idle=round(first['start']-enter-occupied))
    for name in ('starts.txt','window.csv','busy.txt'):
        path=temp/f'nes-credit1004-control-p{phase}'/name
        plan.setdefault('control_trace_sha256',{})[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(plan_trace=plan,first_E9_sensitivity=offer,section5_sensitivity_clocks=sensitivity,head_E8_after_previous_return_clocks=gaps, actual_group_late_clocks=actual['group']-data['vblank46_start'],
                protected=data['protected'],observed_978=data['baseline'],scenarios=scenarios)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    source=ROOT/'analysis/overlap1002-results.json'
    ctrl=ROOT/'analysis/credit1004-results.json'
    inputs = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,ctrl)}
    board=args.temp/'nes-trial816-board964'
    for name in ('nes_direct206.sv','nes_plan_spi200.sv','nes_bulk_aperture188.sv'):
        inputs[name]=hashlib.sha256((board/name).read_bytes()).hexdigest()
    data, control = [json.loads(p.read_text()) for p in (source,ctrl)]
    result = {p:inspect(args.temp,int(p),data[p],control[p]) for p in ('1','2')}
    args.out.write_text(json.dumps(dict(inputs=inputs,phases=result),indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    main()
