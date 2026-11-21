"""Compare the linked map wait against the physical reference and matched wait control."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_deadline875 import analyze, points
from analyze_nes_map830 import load, packets, window
from check_nes_mapwait880 import observation
from check_nes_raster879 import summary
from check_nes_retire878 import trace, verify_retire_order
from check_nes_scroll874 import receipt
from check_nes_strip869 import metrics


def opening(folder, gen):
    events = load(folder / 'events.json')
    rows = [e for e in window(folder) if e['g'] == gen]
    capture = next(e for e in events if e['generation'] == gen and e['event'] == 'source_begin')
    issues = [e for e in events if e.get('opcode') == '0xe1']
    wire = [[b[0], b[1], int.from_bytes(b[10:12], 'little'), int.from_bytes(b[12:14], 'little'),
             round(tx['start'])] for b, tx in zip(packets(folder), issues, strict=True)
            if int.from_bytes(b[8:10], 'little') == gen]
    # Opcode 7 / BG supplies four descriptor bytes. Its extent and offset
    # are independently echoed in the preceding E8 producer snapshot.
    bg = next((item for item in wire if item[:3] == [7, 0, 2048]), None)
    bg_status = None
    if bg:
        polls = [e for e in events if e.get('opcode') == '0xe8' and e['generation'] == gen and
                 e['clock'] <= bg[-1]]
        reply = bytes.fromhex(polls[-1]['reply'])
        assert reply[6] and reply[7] == 0 and int.from_bytes(reply[10:12], 'little') == 2048
        token = int.from_bytes(reply[14:18], 'little')
        producers = map(json.loads, (folder / 'producer.jsonl').read_text().splitlines())
        pub, = [e for e in producers if e['generation'] == gen and e['token'] == token]
        assert pub['kind'] == 0 and pub['bytes'] == int.from_bytes(reply[8:10], 'little')
        bg_status = dict(checked_E8_end=round(polls[-1]['clock']), E1_start=bg[-1],
                         previous_E8_end=round(polls[-2]['clock']), descriptor=reply.hex(), producer=pub)
    return dict(capture_ready=round(capture['capture_ready']), source_begin=round(capture['clock']),
                planner=round(next(e['clock'] for e in events if e['event'] == 'planner_enter' and e['generation'] == gen)),
                wire=wire, bg_2048=bg_status,
                plan_E9=[[e['bytes'], round(e['clock'])] for e in events
                         if e.get('opcode') == '0xe9' and e['generation'] == gen],
                SEAL=[[e['event'], e['clock'], e['frame'], e['line']] for e in rows
                                 if e['op'] == 3 and e['event'] in ('load', 'upload165_entry', 'reveal', 'ack')],
                dma=[[e['frame'], e['line'], e['value']] for e in rows if e['event'] == 'ppu_dma'])


def measured_wait(folder, gen):
    r = receipt(folder, gen)
    start = r['matching_credit'][0]
    polls = [e for e in load(folder / 'events.json') if e.get('opcode') == '0xe0' and
             start <= round(e['start']) < r['scroll_E1_start']]
    return dict(extra_reads=len(polls), bytes=sum(e['bytes'] for e in polls),
                credit=start, scroll=r['scroll_E1_start'], seal=r['seal'],
                show=[r['show'], r['line']], gap=r['gap'], DMA=r['DMA'])


def report(temp, work):
    tag = '881-range'
    result = analyze(temp, work.parents[1], work, tag)
    assert result['guards']['source_tag'] == tag
    result['scattered_guards'] = load(work / 'scrollguard-gap.json')
    result['input951_guards'] = load(work / 'blocks951.json')
    result['retire_guards'] = load(work / 'retire-guards.json')
    assert result['retire_guards']['ARM'] == result['ARM']
    result['phases'] = {}
    for ph in (1, 2):
        def folder(clip, variant=tag):
            return temp / f'nes-tile821-{clip}-jointmirror-p{ph}-{variant}'

        phase = {}
        result['phases'][ph] = phase
        for clip in ('opening', 'transition', 'demo'):
            checked = verify_retire_order(folder(clip))
            assert checked == result['scenes'][f'{clip}-{ph}']['pictures'][-1]
        reference = folder('opening', '872-final')
        def shows(d):
            return {e['g']: e['frame'] for e in window(d) if e['event'] == 'reveal'}
        original = shows(reference)
        later = [g for g, frame in shows(folder('opening')).items() if frame > original[g]]
        if later:
            g = later[0]
            old, new = [opening(p, g) for p in (reference, folder('opening'))]
            mismatch = next((i for i, (a, b) in enumerate(zip(old['wire'], new['wire'])) if a[:4] != b[:4]), None)
            phase['first_late_opening'] = dict(g=g, first_packet_order_change=mismatch,
                                               reference=old, candidate=new)
        transition = folder('transition')
        paired = folder('transition', '881-unconditional')
        assert load(paired / 'joint.json')['firmware_SHA256'] == result['ARM']
        assert verify_retire_order(paired) == verify_retire_order(transition)
        phase['941'] = {name: measured_wait(d, 941) for name, d in [('control', paired), ('candidate', transition)]}
        phase['transition_control_gaps'] = metrics(paired)['after_two_VBlanks']
        past, current = (list(shows(d).items()) for d in (folder('transition', '872-final'), transition))
        assert [g for g, _ in past] == [g for g, _ in current]
        phase['transition_interval_changes'] = [
            [g, f - f0, t1 - t0] for (_, f0), (g, f), (_, t0), (_, t1)
            in zip(past[1:], past[2:], current[1:], current[2:]) if f - f0 != t1 - t0]
        phase['transition_952'] = {name: opening(d, 952) for name, d in
                                   [('reference', folder('transition', '872-final')), ('candidate', transition)]}
        old, new = [load(d / 'events.json') for d in (paired, transition)]
        a, b = [[e for e in events if e['event'] == 'SPI'] for events in (old, new)]
        ix = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
        phase['first_control_SPI_difference'] = dict(index=ix, reference=a[ix], candidate=b[ix])
        phase['950'] = measured_wait(folder('demo'), 950)
        obs = observation(folder('demo'))
        phase['950']['first_progress'] = obs['first_progress']
        edge = points(folder('demo', '874-drain'))['previous_capture_edge']
        t = trace(folder('demo'), edge)
        phase['950_to_952'] = summary(t)
        phase['post_publish'] = t['from_publish']
        static = trace(folder('demo', '878-once'), edge)
        result['gates'][f'demo-{ph}_publish'] = t['show950']['clock'] <= static['show950']['clock']
        result['gates'][f'demo-{ph}_capture'] = t['commit_minus_874_edge'] < 0

        def bus(variant):
            path = temp / f'nes-mapwait880-consumer-{ph}-{variant}'
            with (path / 'idle-vram.csv').open() as f:
                return [tuple(map(int, row)) for row in csv.reader(f)]
        prefix = bus('878-once')
        current = bus(tag)
        assert len(prefix) == 1472
        prior = phase['950']['show'][0] - 1
        phase['950_prefix_equal'] = current[:1472] == prefix
        result['gates'][f'demo-{ph}_950_equivalent'] = (
            phase['950']['gap'] == 3 and phase['950_prefix_equal'] and
            obs['first_progress'] is not None and obs['map']['consecutive'] and
            any(frame == prior and size == 1472 for frame, line, size in phase['950']['DMA']))
        phase['950_idle_bytes'] = len(current)
    result['failed_with_equivalent_DMA'] = [key for key, ok in result['gates'].items()
                                            if not ok and not key.endswith('_950')]
    result['passed_with_equivalent_DMA'] = not result['failed_with_equivalent_DMA']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('work', type=lambda s: Path(s).resolve())
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(report(args.temp, args.work), indent=2) + '\n')
