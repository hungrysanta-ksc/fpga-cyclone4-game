# SPDX-License-Identifier: MIT
"""Compare real firmware schedules at the first blank after the 956 reveal."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_nes_bg750 import counters
from analyze_nes_credit753 import partition
from analyze_nes_owner739 import csv_groups, ms, read, sha
from analyze_nes_static751 import phase


def deadline(folder, previous):
    # A reveal gives a frame and line, but no horizontal clock. Select only
    # hardware counter samples in the following physical frame's blank.
    # An NTSC short scanline can change extrapolation by four master clocks.
    estimate = previous['clock'] + (262 + 249 - previous['line']) * 1364
    samples = counters(folder / 'dma748.csv')
    with (folder / 'seal528.csv').open() as stream:
        for r in csv.DictReader(stream):
            samples.append({k: int(r[k]) for k in ('clock', 'line', 'h')})
    bounds = [r['clock'] + (249 - r['line']) * 1364 - r['h']
              for r in samples if 225 <= r['line'] <= 261]
    nearby = [v for v in bounds if abs(v-estimate) <= 1400]
    assert nearby and max(nearby)-min(nearby) <= 4
    return min(nearby)-4, max(nearby)+4


def schedule(temp, probe, variant, n):
    base = variant == '753'
    folder = temp / (f'nes-credit753-prefix{n}' if base else f'nes-front755-{variant}{n}')
    arm = probe.parent/'nes-credit753/arm-prefix' if base else probe/f'arm-{variant}'
    image = arm/'src/obj-nes-100/firmware.stm'
    digest = sha(image)
    info = phase(temp, 'sharedfast', n, client=probe.parent/'nes-static751/sharedfast',
                 folder=folder, firmware=digest)
    events = read(folder/'events.json')
    windows = csv_groups(folder/'window.csv')
    previous = next(r for r in windows[956] if r['event']=='reveal' and r['op']==3)
    arm_input = partition(folder)
    ack = arm_input['previous_final_ACK']
    begin = next(e for e in events if e['generation']==957 and e['event']=='source_begin')
    first_bg = next(e['start'] for e in events if e['generation']==957 and e.get('opcode')=='0xe9')
    last = next(r['clock'] for r in reversed(windows[957]) if r['section']==2 and r['event']=='ack')
    output = [e for e in events if e['generation']==957]
    maps = [e for e in output if e['event']=='map_packet_enter' and 2048<=e['offset']<3584]
    assert len(maps)==8 and maps[-1]['offset']==3392
    marks = {e['event']: e['clock'] for e in output if e['event'] in ('bg_map_frozen','prepare_enter')}
    marks.update(page_start=maps[0]['clock'], last_offer=maps[-1]['clock'], first_BG_E9=first_bg)
    for packet in ('0xd3','0xea'):
        found = [e for e in events if e.get('opcode')==packet and ack<e['clock']<arm_input['planner']]
        assert len(found)==1
        marks[packet]=found[0]['clock']
    assert ack < marks['0xea'] < marks['0xd3'] < arm_input['planner']

    limit_lo, limit_hi = deadline(folder, previous)
    assert last < limit_lo or last > limit_hi
    spi = [e for e in events if e['event']=='SPI']
    tail = [e for e in spi if ack < e['clock'] <= last]
    bus = sum(max(0, min(last, e['clock'])-max(ack, e['start'])) for e in spi)
    wire = read(folder/'joint.json')['wire_B']
    total_bytes = sum(wire.values())
    # The separate controller observer records 70h/73h outside the SPI event tap.
    assert sum(e['bytes'] for e in spi) == sum(v for k,v in wire.items() if k not in ('0x70','0x73'))
    map_bytes = {g: [r['bytes'] for r in group if r['preseal']] for g,group in info['map_ranges'].items()}
    return dict(firmware=digest, Flash_B=image.stat().st_size, phases=info['intervals'],
        protected=info['guarded_schedule'], public951=info['line951'], wait957=info['final_wait957'],
        map_preseal_B=map_bytes, OBJ_line=info['OBJ']['line'], map_OBJ_order=info['order'],
        map_OBJ_same_blank=all(info['long_map'].values()) and info['margin_to_258'] is not None,
        E8_start_delta749=info['E8_delta_clocks'], E8_end_delta749=info['E8_end']-info['E8_749_end'],
        mean_ms=info['dense_ms'], ACK=info['ACK'], previous_ACK=ack, end248_clock_bounds=[limit_lo,limit_hi],
        last_map_clock=last, late_ms=ms(last-limit_hi), before_first_248=last<limit_lo,
        confirmed_before_956_ACK=arm_input['blocks_before_ACK'], input_blocks=len(arm_input['blocks']),
        since_956_ACK_ms={k:ms(v-ack) for k,v in dict(capture=begin['capture_ready'], input=begin['clock'],
            planner=arm_input['planner'], last_map=last, **marks).items()},
        until_last_map=dict(transactions=len(tail), bytes=sum(e['bytes'] for e in tail),
            occupied_ms=ms(bus), by_opcode=Counter(e['opcode'] for e in tail)),
        run_SPI_B=total_bytes, run_nonobserver_transactions=len(spi), hashes=info['pins'])


def analyze(temp, probe):
    baseline = {n:schedule(temp,probe,'753',n) for n in (1,2)}
    result = dict(reference=baseline, candidates={}, rejected={}, selected='753')
    from analyze_nes_owner739 import packets
    folder = temp/'nes-credit753-prefix1'
    prior = (folder/'map-955.bin').read_bytes()
    current = (folder/'map-957.bin').read_bytes()
    groups = []
    for header, _, _ in packets(folder)[957]:
        start = int.from_bytes(header[10:12],'little')
        if header[:2] != bytes((2,2)) or not 2048 <= start < 3584:
            continue
        body = header[16:]
        assert len(body)==192 and current[start:start+192]==body
        count = sum(prior[i:i+4]!=current[i:i+4] for i in range(start,start+192,4))
        groups.append((start,count))
    assert [start for start,_ in groups]==list(range(2048,3584,192))
    # Fixed eight E1 heads, six bitmap bytes per head and four bytes per set bit.
    # A wire-only bound excludes recovery, independent checking and ARM/65816 time.
    payload = 8*6+4*sum(v for _,v in groups)
    result['map_budget'] = dict(region=[2048,3584],destination_history=955,
        changed_B=sum(a!=b for a,b in zip(prior[2048:3584],current[2048:3584])),
        groups=groups, masked_payload_B=payload, wire_only_saving_ms=(1536-payload)*8/2625,
        prior_sha=sha(folder/'map-955.bin'), current_sha=sha(folder/'map-957.bin'))
    for variant in ('wire','receive','index','joint','fast','empty','service','paired','geometry'):
        pair = {}
        for n in (1,2):
            r = schedule(temp,probe,variant,n)
            b = baseline[n]
            r['dense_delta_ms'] = r['mean_ms']-b['mean_ms']
            r['ACK_delta_ms'] = ms(r['ACK']-b['ACK'])
            r['qualified'] = (r['before_first_248'] and r['phases'][957]==2 and r['protected']
                and r['OBJ_line']<=256 and max(r['E8_start_delta749'],r['E8_end_delta749'])<=0
                and r['dense_delta_ms']<0 and r['ACK_delta_ms']<0 and r['Flash_B']<=212992)
            pair[n] = r
        result['candidates'][variant] = pair
        if all(r['qualified'] for r in pair.values()):
            result['selected'] = variant
    for variant,reason in [('stream','not an empty output queue'),('frozen',"'runtime fault', 907, 5, 4")]:
        pair = {}
        for n in (1,2):
            log = temp/f'nes-front755-{variant}{n}.log'
            assert reason in log.read_text(encoding='utf8')
            pair[n] = dict(error=reason, log=sha(log))
        result['rejected'][variant] = pair
    result['ARM_faults'] = {}
    for variant in ('geometry','receive'):
        guard = read(probe/f'late-{variant}.json')
        assert guard['firmware']==result['candidates'][variant][1]['firmware']==guard['menu']['firmware']
        result['ARM_faults'][variant]=guard
    result['receiver_faults']={n:{fault:read(temp/f'nes-front755-wireguard-{n}-{fault}/verified751.json')
        for fault in ('before','during','head','stale')} for n in (1,2)}
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','probe','out'):
        parser.add_argument('--'+name, type=Path, required=True)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe), indent=2)+'\n', encoding='utf8')
