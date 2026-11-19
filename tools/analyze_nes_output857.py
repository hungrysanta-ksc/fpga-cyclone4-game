"""Compare released and candidate schedules on exact source frames and section-5 data."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_nes_map830 import load, packets, window
from analyze_nes_output822 import CLK_MS
from analyze_nes_output852 import measure
from analyze_nes_output856 import credit_windows
from check_nes_game478 import sha
from prepare_nes_trial802 import PROBES


def missed_edge_us(directory, wait, resume):
    if wait['line'] < 225 or resume['frame'] != wait['frame']+1:
        return None
    with (directory/'seal528.csv').open() as trace:
        edges = sorted({int(row['clock'])-int(row['h']) for row in csv.DictReader(trace)
                        if row['line'] == '225'})
    # Only use observed adjacent frame lengths. The parity of the missed
    # edge is not logged, so retain the short-line uncertainty.
    periods = {b-a for a,b in zip(edges,edges[1:]) if 357360 <= b-a <= 357370}
    assert periods == {357364,357368}
    candidates = [c for c in edges if 0 <= resume['clock']-c < 1364]
    if not candidates:
        return None
    edge, = candidates
    return [round((wait['clock'] - edge + t) * 1000 / CLK_MS, 2) for t in sorted(periods)]


def section5(directory):
    data = {}
    for p in packets(directory):
        if p[1] != 5:
            continue
        op = p[0]
        assert op in (2, 4, 5)
        generation = int.from_bytes(p[8:10], 'little')
        offset = int.from_bytes(p[10:12], 'little')
        payload = p[16:]
        if op in (4, 5):
            size = int.from_bytes(p[14:16], 'little')
            assert len(payload) == 2 and size and not size % 2
            payload *= size // 2
        image = data.setdefault(generation, bytearray())
        assert len(image) == offset
        image.extend(payload)
    return data


def timing(directory, generation):
    trace = window(directory)
    previous_show, = [e for e in trace if e['g'] == generation-1 and e['event'] == 'reveal']
    events = [e for e in trace if e['g'] == generation]
    obj = max(e['clock'] for e in events
              if e['event'] == 'ack' and (e['op'], e['section']) == (7, 1))
    seal, = [e for e in events if e['event'] == 'load' and e['op'] == 3]
    waits = [e for e in events if e['event'] == 'wait169' and e['clock'] >= seal['clock']]
    wait_ms = 0
    missed = None
    for wait in waits:
        resume = next(e for e in events if e['clock'] > wait['clock']
                      and (e['event'].startswith('wait_return') or e['event'] == 'final_upload212_same_blank212'))
        wait_ms += (resume['clock']-wait['clock'])/CLK_MS
        if wait['line'] >= 225:
            missed = missed_edge_us(directory,wait,resume)
    show, = [e for e in events if e['event'] == 'reveal']
    link = load(directory / 'events.json')
    issued = [e for e in link if e.get('opcode') == '0xe1']
    counts = Counter()
    time = Counter()
    for e in link:
        if e['event'] != 'SPI':
            continue
        left, right = max(obj, e['start']), min(seal['clock'], e['clock'])
        if right > left:
            counts[e['opcode']] += 1
            time[e['opcode']] += right - left
    packets_after_obj = []
    for e in events:
        if e['event'] == 'load' and obj < e['clock'] <= seal['clock']:
            transaction = issued[e['index'] - 1]
            assert transaction['generation'] == generation and transaction['packet_opcode'] == e['op']
            packets_after_obj.append(dict(op=e['op'], section=e['section'],
                issued_ms=round((transaction['clock']-obj)/CLK_MS,4),
                loaded_ms=round((e['clock']-obj)/CLK_MS,4)))
    return dict(obj_return=obj, SEAL_load=seal['clock'], SEAL_line=seal['line'],
                OBJ_to_SEAL_ms=round((seal['clock']-obj)/CLK_MS, 5),
                previous_reveal_to_OBJ_ms=round((obj-previous_show['clock'])/CLK_MS,5),
                previous_reveal_to_SEAL_ms=round((seal['clock']-previous_show['clock'])/CLK_MS,5),
                SPI_counts=counts, SPI_ms={k:round(t/CLK_MS,5) for k,t in time.items()},
                packet_loads_after_OBJ=packets_after_obj, wait_lines=[w['line'] for w in waits],
                wait_ms=round(wait_ms,5), wait_entry_after_missed_edge_us=missed,
                reveal=show['clock'], reveal_frame=show['frame'])


def compare(temp, clip, phase, tag):
    baseline = '856-855' if clip == 'demo' else '857ref'
    prefix = f'nes-tile821-{clip}-jointmirror-p{phase}-'
    result = {}
    previous = None
    gaps = {}
    for label in (baseline, tag):
        directory = temp / (prefix + label + '-on')
        metrics, geometry, _ = measure(temp, clip, phase, 'on', label, column=True)
        raw = section5(directory)
        joint = load(directory/'joint.json')
        events = load(directory/'events.json')
        spi = [e for e in events if e['event'] == 'SPI']
        full = credit_windows(spi,window(directory))
        comparable = raw, geometry, joint['parameters']
        if previous is not None:
            assert previous == comparable
        previous = comparable
        link = (PROBES/'nes-trial855/link' if label == baseline
                else PROBES/'nes-output857'/('link-'+label.removeprefix('857')))
        firmware = link/'src/obj-nes-100/firmware.stm'
        assert sha(firmware) == metrics['arm']
        result[label] = {k: metrics[k] for k in ('arm', 'client', 'display_VBlanks', 'final_ACK',
                                                 'held_blank_VBlanks', 'verified_pictures')}
        result[label]['flash_bytes'] = firmware.stat().st_size
        result[label]['verified_full_queue_intervals'] = len(full)
        result[label]['ARM_observed_stack_low'] = joint['observed_stack_low']
        gaps[label] = metrics['gaps']
        if clip == 'demo':
            work = load(temp/'nes-comparison851/demo/demo/work.json')
            g = next(w['g'] for w in work if w['source_frame'] == 2616)
            idx = next(i for i,w in enumerate(work[2:]) if w['g'] == g)
            result[label]['source2616'] = dict(gap=metrics['gaps'][idx], **timing(directory,g))
            prior_ack = next(f['ACK_masterclock'] for f in joint['frames'] if f['generation'] == g)
            ready = next(e['capture_ready'] for e in events
                         if e['event']=='source_begin' and e['generation']==g+1)
            first_read = next(e['start'] for e in spi
                              if e['opcode']=='0xd1' and e.get('input_generation')==g+1)
            pops = [e['clock'] for e in spi if e['opcode']=='0xd2' and e.get('input_generation')==g+1]
            assert len(pops) == 17
            result[label]['source2617'] = dict(gap=metrics['gaps'][idx+1], total_D2=len(pops),
                capture_ready_to_previous_ACK_ms=round((prior_ack-ready)/CLK_MS,5),
                capture_ready_to_first_D1_ms=round((first_read-ready)/CLK_MS,5),
                D2_before_previous_final_ACK=sum(t <= prior_ack for t in pops),
                last_D2_after_previous_ACK_ms=round((pops[-1]-prior_ack)/CLK_MS,5))
            following = [e for e in window(directory) if e['g']==g+1 and e['op']==3]
            waits = [e for e in following if e['event']=='wait169']
            if waits:
                wait = waits[-1]
                resume = next(e for e in following if e['clock']>wait['clock'] and
                              (e['event'].startswith('wait_return') or e['event']=='final_upload212_same_blank212'))
                result[label]['source2617'].update(wait_line=wait['line'],
                    wait_entry_after_missed_edge_us=missed_edge_us(directory,wait,resume))
    a,b = result.values()
    assert a['client']==b['client']
    fixtures = temp / ('nes-trans850-c0' if clip == 'transition' else 'nes-comparison851')
    sources = load(fixtures/clip/clip/'work.json')[2:]
    changes = [[w['source_frame'], old, new] for w,old,new in
               zip(sources,gaps[baseline],gaps[tag],strict=True) if old != new]
    return dict(runs=result, gap_delta=b['display_VBlanks']-a['display_VBlanks'],
                ACK_delta_ms=round((b['final_ACK']-a['final_ACK'])/CLK_MS,5),
                changed_intervals=changes)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('tag', nargs='+')
    parser.add_argument('--controls', nargs='*', default=[],
                        help='Candidates also exercised on the full opening and transition')
    args = parser.parse_args()
    report = {tag:{clip:{p:compare(args.temp,clip,p,tag) for p in (1,2)}
                   for clip in (('opening','transition','demo') if tag in args.controls else ('demo',))}
              for tag in args.tag}
    probe = PROBES/'nes-output857'
    sizes = {}
    for variant in 'abcdefgh':
        fw = probe/f'link-{variant}/src/obj-nes-100/firmware.stm'
        sizes[variant] = dict(bytes=fw.stat().st_size, headroom=212992-fw.stat().st_size,
                              sha256=sha(fw))
    guards = {}
    for tag in args.controls:
        variant = tag.removeprefix('857')
        menu = load(probe/f'{variant}-menu.json')
        base = load(probe/f'{variant}-stop/result.json')
        assert menu['firmware'] == base['firmware_sha256'] == sizes[variant]['sha256']
        assert base['safe_return'] and base['base_restored']
        guards[tag] = dict(menu_cases=sorted(menu['rows']), base_restored=True,
                           consumer=load(probe/f'{variant}-consumer.json'),
                           stop=load(probe/f'{variant}-stop.json'),
                           identity=load(probe/f'{variant}-identity.json'))
        if variant == 'h':
            guards[tag]['raw_successor_stop'] = load(probe/'h-raw-stop.json')
    args.out.write_text(json.dumps(dict(replays=report, builds=sizes, guards=guards),
                                   indent=2)+'\n')
