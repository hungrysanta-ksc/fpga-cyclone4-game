"""Compare the actual OAM, tables, SEAL, DMA and display clocks at matched workload."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_nes_deadline875 import analyze, points
from analyze_nes_map830 import load, packets, window
from check_nes_mapgate881 import measured_wait
from check_nes_retire878 import trace, verify_retire_order
from check_nes_strip869 import metrics
from test_nes_service509_schedule import Calendar


def target(d):
    data = packets(d)
    spi = [e for e in load(d/'events.json') if e.get('opcode') == '0xe1']
    events = window(d)
    heads = {e['index']: e for e in events if e['event'] == 'load'}
    acks = {e['index']: e for e in events if e['event'] == 'ack'}
    gen = 952
    trace = []
    canonical = []
    for i, (b, tx) in enumerate(zip(data, spi, strict=True), 1):
        if int.from_bytes(b[8:10], 'little') != gen:
            continue
        # Normalize only the queue sequence field. Retain identity and payload.
        canonical.append(b[:2] + b[4:])
        trace.append(dict(op=b[0], section=b[1], offset=int.from_bytes(b[10:12], 'little'),
                          wire=tx['bytes'], issue=round(tx['start']), sent=round(tx['clock']),
                          accept=heads[i]['clock'], retire=acks[i]['clock']))
    assert trace[-1]['op'] == 3 and not any(e['section'] == 2 for e in trace)
    show = [e for e in events if e['event'] == 'reveal' and e['g'] in (951, gen)]
    assert len(show) == 2
    return canonical, dict(packets=trace, show=show[1], previous=show[0], gap=show[1]['frame']-show[0]['frame'],
                           DMA=[[e['frame'],e['line'],e['value']] for e in events
                                if e['g'] == gen and e['event'] == 'ppu_dma'])


def capture(d, g):
    events = load(d/'events.json')
    s = next(e for e in events if e['event'] == 'source_begin' and e['generation'] == g)
    pop = next(e for e in reversed(events) if e.get('opcode') == '0xd2' and e.get('input_generation') == g-1)
    ack = next(e for e in window(d) if e['g']==g-2 and e['op']==3 and e['event']=='ack')
    ea = next(e for e in events if e.get('opcode')=='0xea' and e['generation']==g-2)
    expected = next(b for b in packets(d) if b[0]==3 and int.from_bytes(b[8:10],'little')==g-2)
    wanted = bytes([1,3])+expected[2:10]+bytes.fromhex('659a')
    e0 = next(e for e in events if e.get('opcode')=='0xe0' and ack['clock']<=e['clock']<ea['start']
              and bytes.fromhex(e['reply'])[7:19]==wanted)
    return dict(prior_display_ACK=ack['clock'], valid_E0=round(e0['clock']), EA=round(ea['clock']),
                D2=round(pop['clock']), ready=round(s['capture_ready']), start=round(s['clock']))


def bg_grants(temp):
    records = []
    batches = []
    for variant in ('872-final', '881-range'):
        d = temp/f'nes-tile821-opening-jointmirror-p1-882-cold-{variant}'
        with (d/'bg-grants.csv').open() as f:
            records.append([{k:int(v) for k,v in row.items()} for row in csv.DictReader(f)
                            if row['generation'] == '906'])
        batches.append([[e['bytes'],round(e['start']),round(e['clock'])] for e in load(d/'events.json')
                        if e.get('opcode') == '0xe9' and e['generation'] == 906])
    a, b = records
    assert a and [r['address'] for r in a] == [r['address'] for r in b]
    # Crossing the long interval between ROM windows is visible as a sharp
    # jump in paired response clocks. Keep both transient and persistent jumps.
    previous = 0
    jumps = []
    for i, (old, new) in enumerate(zip(a, b)):
        delta = new['response'] - old['response']
        if abs(delta - previous) > 250000:
            jumps.append(dict(index=i, delta=delta, prior_delta=previous, reference=old, candidate=new))
        previous = delta
    assert [r[0] for r in batches[0]] == [r[0] for r in batches[1]]
    index = jumps[-1]['index']
    clock = Calendar(temp/'nes-service509-rom03')
    def gaps(rows):
        return [v['request'] - u['response'] for u,v in zip(rows[index:],rows[index+1:])]
    spacing = gaps(a)
    assert spacing == gaps(b)
    def last_response(start):
        end = clock.select(start)[1]
        for cost in spacing:
            end = clock.select(end + cost)[1]
        return end
    early, late = a[index]['request'], b[index]['request']
    assert last_response(early) == a[-1]['response'] and last_response(late) == b[-1]['response']
    # Find the latest first request that still fits the same window as the
    # reference. The observed gaps retain cache hits and tile decode costs.
    while early + 1 < late:
        middle = (early + late)//2
        if last_response(middle) < b[index]['grant']:
            early = middle
        else:
            late = middle
    return dict(count=len(a), jumps=jumps, last=[a[-1], b[-1]], E9=batches,
                final_run=dict(reads=len(spacing)+1, deadline=early, advance=b[index]['request']-early,
                               last_if_on_time=last_response(early), last_if_one_clock_late=last_response(late)))


def report(temp, work, tag):
    out = analyze(temp, work.parents[1], work, tag)
    assert out['guards']['source_tag'] == tag
    out['retire_guards'] = load(work/'retire-guards.json')
    assert out['retire_guards']['ARM'] == out['ARM']
    out['fragmented_scroll'] = load(work/'scrollguard-gap.json')
    out['phases'] = {}
    out['opening_BG_906'] = bg_grants(temp)
    for ph in (1, 2):
        def folder(clip, version=tag):
            return temp/f'nes-tile821-{clip}-jointmirror-p{ph}-{version}'
        phase = {}
        out['phases'][ph] = phase
        for clip in ('opening', 'transition', 'demo'):
            assert verify_retire_order(folder(clip)) == out['scenes'][f'{clip}-{ph}']['pictures'][-1]
            def seals(version):
                return [b[8:] for b in packets(folder(clip,version)) if b[0] == 3]
            assert seals(tag) == seals('881-range')
        src = folder('transition')
        paired = folder('transition', '882-late952' if tag == '882-oam' else '881-range')
        contents, new = target(src)
        base_contents, late = target(paired)
        assert Counter(contents) == Counter(base_contents)
        oam = next(i for i,e in enumerate(new['packets']) if e['op'] == 9)
        assert late['packets'][-2]['op'] == 9
        out['gates'][f'transition-{ph}_oam_first'] = new['packets'][oam + 1]['section'] == 5
        if tag == '882-oam':
            assert load(paired/'joint.json')['firmware_SHA256'] == out['ARM']
            assert verify_retire_order(paired) == verify_retire_order(src)
            assert new['previous'] == late['previous']
            streams = [[e for e in load(d/'events.json') if e['event']=='SPI'] for d in (src, paired)]
            ix = next(i for i,(a,b) in enumerate(zip(*streams)) if a != b)
            assert all(s[ix]['generation']==952 for s in streams)
            assert (src/'frame-952.rgb').read_bytes() == (paired/'frame-952.rgb').read_bytes()
            phase['first_control_SPI_difference'] = dict(index=ix, clocks=[round(s[ix]['start']) for s in streams])
        phase['transition_952'] = dict(candidate=new, control=late, parent=target(folder('transition','881-range'))[1])
        phase['transition_control_intervals'] = metrics(paired)['after_two_VBlanks']
        phase['transition_941'] = measured_wait(src, 941)
        phase['dense_950'] = measured_wait(folder('demo'), 950)
        parent_demo = folder('demo','881-range')
        phase['dense_interval_changes'] = []
        old, new_shows = [[(e['g'],e['frame']) for e in window(path) if e['event'] == 'reveal']
                          for path in (parent_demo, folder('demo'))]
        assert [g for g,_ in old] == [g for g,_ in new_shows]
        for i in range(2,len(old)):
            prev, cur = old[i][1]-old[i-1][1], new_shows[i][1]-new_shows[i-1][1]
            if cur != prev:
                phase['dense_interval_changes'].append([old[i][0],prev,cur])
        phase['dense_910_capture'] = {name:capture(path,910) for name,path in
                                      [('881',parent_demo),('candidate',folder('demo'))]}
        edge = points(folder('demo','874-drain'))['previous_capture_edge']
        timing = trace(folder('demo'), edge)
        base = trace(folder('demo','881-range'), edge)
        phase['post_publish'] = timing['from_publish']
        out['gates'][f'demo-{ph}_950_publish_clock'] = timing['show950']['clock'] <= base['show950']['clock']
        out['gates'][f'demo-{ph}_951_capture'] = timing['commit_minus_874_edge'] < 0
        def audit(version):
            with (temp/f'nes-mapwait880-consumer-{ph}-{version}/idle-vram.csv').open() as f:
                return [tuple(map(int,row)) for row in csv.reader(f)]
        actual, parent = audit(tag), audit('881-range')
        assert len(parent) == 1536
        phase['dense_950']['idle_bytes'] = len(actual)
        phase['dense_950']['matched_address_port_value'] = actual == parent
        m = phase['dense_950']
        out['gates'][f'demo-{ph}_same_DMA'] = (actual == parent and m['gap'] == 3 and
                                               [n for f,_,n in m['DMA'] if f == m['show'][0]-1][:2] == [1472,64])
        out['gates'][f'transition-{ph}_941'] = (phase['transition_941']['show'][0] <= 118 and
                                                phase['transition_941']['extra_reads'] == 0)
        out['gates'][f'transition-{ph}_952'] = new['gap'] == 1 and new['show']['frame'] <= 140
        previous = metrics(folder('demo', '881-range'))
        current = metrics(folder('demo'))
        out['gates'][f'demo-{ph}_retain881'] = (current['after_two_VBlanks'] <= previous['after_two_VBlanks']
                                                and current['last_ACK'] <= previous['last_ACK'])
    out['failed_with_equivalent_DMA'] = [k for k,v in out['gates'].items() if not v and not k.endswith('_950')]
    out['passed_with_equivalent_DMA'] = not out['failed_with_equivalent_DMA']
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('probes', type=lambda s:Path(s).resolve())
    parser.add_argument('out', type=Path)
    a = parser.parse_args()
    reports = {tag:report(a.temp, a.probes/directory, tag) for directory,tag in [
        ('nes-oam882','882-oam'), ('nes-oam882-single','882-single'), ('nes-oam882-direct','882-direct')]}
    a.out.write_text(json.dumps(reports, indent=2) + '\n')
