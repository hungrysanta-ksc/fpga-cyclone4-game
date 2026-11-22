"""Partition section-5 acceptance to last OBJ publication on the shared clock."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path

from analyze_nes_section909 import measure, coverage
from analyze_nes_section910 import guards, ms
from nes_section910 import BASE, sha
from replay_nes_rows911 import AheadLink
from test_nes_obj609 import lanes
from test_nes_raw506_joint import wire_plan
from test_nes_service509_schedule import Calendar


def read(path, name):
    return json.loads((path/name).read_bytes())


def missed_windows(temp, path, start, end):
    """In a forced capture miss every enabled low row needs one physical grant."""
    plans = [bytes.fromhex(q) for _,q in read(temp/'nes-gap904/data-obj/obj/frame912','plans.json')]
    slots = {(int(q[6]==1),int.from_bytes(q[2:4],'little')*(32 if q[6]==1 else 16)):q
             for q in plans if q[6] < 3}
    batches = read(path,'banks904.json')['912']['banks557']
    plan_number = 0
    rows = []
    for line in (path/'packets.jsonl').read_text().splitlines():
        b = bytes.fromhex(json.loads(line)[2])
        if b[0] != 7 or int.from_bytes(b[8:10],'little') != 912:
            continue
        offset = int.from_bytes(b[10:12],'little')
        n = int.from_bytes(b[14:16],'little')
        token = int.from_bytes(b[16:20],'little')
        for i in range(offset,offset+n,32 if b[1] else 16):
            q = slots[b[1],i]
            batch, = [v for v in batches if v['first']<=plan_number<v['first']+v['count']]
            if b[1]:
                rows.extend((token,i,addr,batch) for lane,addr in lanes(q) if lane%2 == 0)
            plan_number += 1
    assert plan_number == len(slots) == sum(v['count'] for v in batches)-1
    all_grants = read(path,'grants904.json')
    grants = [r for r in all_grants if r[:2] == [912,1]]
    used = {r[3] for r in all_grants}
    assert len(rows) == len(grants)
    calendar = Calendar(temp/'nes-service509-rom03')
    misses = []
    for (token,offset,addr,batch), (_,_,req,grant,reply) in zip(rows,grants):
        if min(end,grant)-max(start,req) < 21478:  # more than 1 ms within the window
            continue
        cycle, pos = divmod(req,calendar.period)
        i = bisect_left(calendar.starts,pos)
        prior = calendar.starts[i-1]+(cycle-(i==0))*calendar.period
        assert prior < req and calendar.select(req) == (grant,reply)
        # A feasibility count, conditional on a second validated descriptor reader.
        # Charge a full short-descriptor scan after the first actual CHECK.
        max_record = max(len(wire_plan(q)) for q in plans)
        begin = batch['first_check']+batch['count']*(2*max_record+4)
        free = 0
        if begin < prior:
            for period in range(int(begin//calendar.period),int(prior//calendar.period)+1):
                base = period*calendar.period
                free += sum(begin<=base+g<=prior and base+g not in used
                            for g in calendar.starts)
        misses.append(dict(token=token,destination=offset,CHR=addr,request=req,
                           unused_prior_slots_after_batch_scan=free,
                           request_after_prior_grant_ms=ms(req-prior),
                           total_wait_ms=ms(grant-req),charged_wait_ms=ms(grant-max(start,req))))
    return misses


def partition(path, frame):
    table = frame['section5_pair'][-1]
    assert table['bytes'] == 240
    start, end = table['accept'], frame['masterclocks']['last_OBJ']
    trace = read(path, 'rows911.json')
    grants = [r for r in read(path, 'grants904.json') if r[0] == 912]
    result = dict(start=start, end=end, relative_ms=ms(end-start),
                  generation_OBJ_grants=sum(r[1] == 1 for r in grants),
                  generation_saved=trace['saved'].get('912', 0))
    if end <= start:
        return result
    spans = []
    def add(label, left, right):
        lo, hi = max(start, left), min(end, right)
        if hi > lo:
            spans.append((lo,hi,label))
    returns = dict(read(path, 'returns904.json'))
    for token, (g, done) in trace['blocked'].items():
        if g == 912:
            add('bank_return', done, returns[int(token)])
    count = 0
    for _, kind, req, grant, reply in grants:
        if reply <= start or req >= end:
            continue
        assert kind == 1
        count += 1
        add('request_to_grant', req, grant)
        add('grant_to_reply', grant, reply)
    totals = dict(request_to_grant=0, grant_to_reply=0, bank_return=0, residual=0)
    cursor = start
    for lo, hi, label in sorted(spans):
        assert cursor <= lo, (cursor,lo,hi,label)
        totals['residual'] += lo-cursor
        totals[label] += hi-lo
        cursor = hi
    totals['residual'] += end-cursor
    assert sum(totals.values()) == end-start
    result.update(grants_in_window=count, masterclocks=totals,
                  ms={key:ms(value) for key,value in totals.items()},
                  top_grant_waits_ms=sorted((ms(hi-lo) for lo,hi,k in spans
                                             if k=='request_to_grant'), reverse=True)[:2])
    return result


def stop_edges(path,calendar):
    # Inject STOP around an actual speculative transaction, including restart
    # with the same numerical generation. Normal ARM menu cleanup is checked
    # separately on the unchanged linked firmware.
    g,addr,grant,reply = read(path,'ahead911.json')[-1]
    for edge in range(grant,reply+2):
        port = object.__new__(AheadLink)
        port.owner = port.generation = g
        port.peer = (g,addr+8)
        port.queue = [(addr+1,edge)]
        port.ready_rows = {addr:(reply,0x55,0xaa)}
        port.free = reply+1
        port.cancel_supply()
        port.pump(edge)
        assert port.owner is None and not port.active and not port.ready_rows and not port.queue
        assert port.peer is None and port.stopped
        port.restart_supply()
        assert port.owner==g and not port.ready_rows and not port.active
        port.original_select = calendar.select
        port.grants = []
        port.read_kind = 1
        next_grant,_ = port.select(edge)
        assert next_grant > reply
    return dict(edges=reply-grant+2,token_generation=g,grant=grant,reply=reply)


def audit(temp,tag):
    data = {}
    for phase in (1,2):
        for cache in ('warm','cold'):
            def path(build):
                return temp/f'nes-tile821-obj-jointmirror-p{phase}-{build}-{cache}-pair'
            baseline, packets = measure(path('907'), BASE)
            old, old_packets = measure(path('911ref'), BASE)
            assert (old,old_packets) == (baseline,packets)
            new, new_packets = measure(path(tag), BASE)
            assert old['parameters'] == new['parameters'] and old['client'] == new['client']
            for g in packets:
                # Scheduling can interleave ordinary packets with ready tiles.
                # Check full bytes and order independently on each original stream.
                for tile in (False, True):
                    assert ([b for b in old_packets[g] if (b[0]==7)==tile] ==
                            [b for b in new_packets[g] if (b[0]==7)==tile])
                assert sha(path('907')/f'frame-{g}.rgb') == sha(path(tag)/f'frame-{g}.rgb')
            frames = {}
            for g, prior in old['frames'].items():
                candidate = new['frames'][g]
                assert prior['section5_hash'] == candidate['section5_hash']
                before = coverage(old['preDMA'][g])
                after = coverage(new['preDMA'][g])
                frames[g] = dict(display=[prior['VBlank'][3],candidate['VBlank'][3]],
                                 early_bytes=[len(before),len(after)],
                                 lost_bytes=len(before.keys()-after.keys()),
                                 later_bytes=sum(before[k]<after[k] for k in before.keys()&after.keys()))
            data[f'p{phase}-{cache}'] = dict(
                reference=partition(path('911ref'),old['frames'][912]),
                candidate=partition(path(tag),new['frames'][912]),
                intervals=[old['intervals'],new['intervals']],
                final_ACK=[old['final_ACK'],new['final_ACK']],
                ACK_delta_ms=ms(new['final_ACK']-old['final_ACK']),
                ARM_E0_delta_ms=ms(new['frames'][912]['masterclocks']['E0_response']-
                                   old['frames'][912]['masterclocks']['E0_response']),
                frames=frames)
            if tag=='911ahead':
                spec=read(path(tag),'ahead911.json')
                data[f'p{phase}-{cache}']['candidate']['generation_background_grants']=sum(r[0]==912 for r in spec)
                data[f'p{phase}-{cache}']['model_STOP']=stop_edges(path(tag),Calendar(temp/'nes-service509-rom03'))
                for key,build in [('reference','911ref'),('candidate',tag)]:
                    total=len(read(path(build),'grants904.json'))+(len(spec) if build==tag else 0)
                    data[f'p{phase}-{cache}'][key]['eight_frame_physical_grants']=total
            if cache=='cold':
                result=data[f'p{phase}-{cache}']['reference']
                result['missed_windows']=missed_windows(temp,path('911ref'),result['start'],result['end'])
    return dict(ARM_checks=guards(BASE), conditions=data)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    args = p.parse_args()
    args.out.write_text(json.dumps({tag:audit(args.temp,tag) for tag in ('911','911ahead')},indent=2)+'\n',encoding='utf8')
