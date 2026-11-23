"""Attribute MMC925 hardware latency and compare the two final-link SPI/PPU traces."""
import argparse
import csv
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from read_nes_supply905 import MS, ROW, decode

ROOT = Path(__file__).resolve().parents[1]
MASTER_PER_MS = 21477.272
MATCH = ('BG', 'OBJ', 'map', 'bank', 'tiles', 'chunks', 'last_kind', 'last_bytes', 'last_offset')


def read_budget(path):
    text = path.read_text(encoding='utf-8-sig')
    columns = re.search(r'^columns=(.+)$', text, re.M)[1].strip().split(',')
    bins = {int(i): dict(zip(columns, (int(v, 16) for v in line.split(',')), strict=True))
            for i, line in re.findall(r'^b(\d\d)=([0-9a-f,]+)$', text, re.M)}
    assert len(bins) == 12 and 'tick_ms=10\n' in text
    def average(start):
        total = Counter()
        for i in range(start, 12):
            total.update(bins[i])
        frames = total['frames']
        return dict(frames=frames, recv_ticks=total['recv'],
                    **{k: round(total[k] * 10 / frames, 4) for k in ('recv', 'plan', 'seal')},
                    **{k: round(total[k] / frames, 4) for k in
                       ('d1_payload', 'd0_clock', 'ingress', 'bg', 'obj', 'mapdirty')})
    return {'30-60': average(6), '55-60': average(11)}


def hardware(path):
    raw = path.read_bytes()
    trace = decode(path, 925)
    assert trace['dropped'] == [0, 0] and trace['mode'] == 0
    groups = defaultdict(list)
    for i, row in enumerate(trace['rows']):
        assert 'invalid' not in row
        if not row['chunks']:
            continue
        _, _, _, _, ack_age, probe, *_, header, _ = ROW.unpack_from(raw, 16 + i * ROW.size)
        _, anchor, head = struct.unpack_from('<3H', header, 6)
        tail = (((anchor - head) & 1023) - (ack_age + probe / 2) / 64) * MS
        groups[tuple(row[k] for k in MATCH)].append(dict(
            generation=row['generation'], tick=row['tick'], E9_head=row['E9_to_last_publish_ms'],
            head_ACK=round(tail, 3), head_ACK_error=round(MS * (1 + (probe / 2 + 2) / 64), 3),
            input_ACK=row['input_to_final_ACK_ms']))
    return [dict(work=dict(zip(MATCH, key)), rows=rows) for key, rows in groups.items() if len(rows) > 1]


def input_partition(events, g):
    # First D1 start through the D0 confirming the last D2 (including COMMIT).
    bus = [e for e in events if e['event'] == 'SPI']
    reads = [i for i, e in enumerate(bus) if e.get('input_generation') == g and e['opcode'] == '0xd1']
    spans = Counter()
    for i in reads:
        read, pop, confirm = bus[i:i+3]
        assert pop['opcode'] == '0xd2' and confirm['opcode'] == '0xd0'
        assert read['start'] < read['clock'] <= pop['start'] < pop['clock'] <= confirm['start'] < confirm['clock']
        assert pop['input_generation'] == confirm['input_generation'] == g
        spans['D1'] += read['clock'] - read['start']
        spans['CRC_restore_guard'] += pop['start'] - read['clock']
        spans['D2_confirm'] += confirm['clock'] - pop['start']
    first, last = reads[0], reads[-1] + 2
    covered = {j for i in reads for j in (i, i+1, i+2)}
    for j in range(first, last+1):
        if j not in covered:
            e = bus[j]
            kind = 'other_input_SPI' if e['opcode'] in ('0xd0','0xd3') else 'other_SPI'
            spans[kind] += e['clock'] - e['start']
    # Observer entries have only an end stamp. Their cost stays in residual.
    duration = bus[last]['clock'] - bus[first]['start']
    spans['between_transactions'] = duration - sum(spans.values())
    assert min(spans.values()) >= 0
    return {k: v / MASTER_PER_MS for k, v in spans.items()} | {'span': duration / MASTER_PER_MS}


def replay(directory, tag, edition):
    joint = json.loads((directory/'joint.json').read_bytes())
    package = json.loads((ROOT/f'analysis/trial{edition}-package.json').read_bytes())
    assert joint['passed'] and joint['firmware_SHA256'] == package['firmware']
    assert joint['client_SHA256'] == package['client']
    events = json.loads((directory/'events.json').read_bytes())
    inputs = [input_partition(events, g) for g in range(907, 913)]
    with (directory/'window.csv').open() as stream:
        window = list(csv.DictReader(stream))
    with (directory/'seal528.csv').open() as stream:
        ports = list(csv.DictReader(stream))
    frames = {}
    for g in range(907, 913):
        rows = [r for r in window if int(r['g']) == g and r['op'] == '3']
        seal, = [r for r in rows if r['event'] == 'load']
        show, = [r for r in rows if r['event'] == 'reveal']
        dmas = [r for r in rows if r['event'] == 'ppu_dma']
        wait = next((r for r in rows if r['event'] == 'wait169'
                     and int(r['clock']) < int(dmas[0]['clock'])), None)
        ppu = [r for r in ports if int(r['g']) == g and r['event'] == 'dma'
               and int(seal['clock']) <= int(r['clock']) <= int(show['clock'])]
        for start, port in zip(dmas, ppu, strict=True):
            assert start['value'] == port['bytes'] and abs(int(start['clock'])-int(port['clock'])) < 200
        frames[g] = dict(seal=[int(seal['frame']), int(seal['line'])],
                         show=[int(show['frame']), int(show['line'])],
                         wait_entry_to_first_dma_ms=(
                             round((int(dmas[0]['clock']) - int(wait['clock'])) / MASTER_PER_MS, 4)
                             if wait else None),
                         post_seal_dma=[[int(r['frame']),int(r['line']),int(p['port']),int(p['bytes'])]
                                        for r,p in zip(dmas,ppu)])
    return dict(edition=tag, input_mean_ms={k:round(mean(r.get(k,0) for r in inputs),4)
                                            for k in sorted(set.union(*(set(r) for r in inputs)))},
                frames=frames)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', type=Path)
    p.add_argument('traces', type=Path)
    a = p.parse_args()
    result = dict(budgets={n:read_budget(a.logs/f'nes-budget-mmc{n}.txt') for n in (915,925)},
                  physical_groups=hardware(a.logs/'nes-frame-mmc925.bin'), replays={})
    for phase in (1,2):
        for cache in ('warm','cold'):
            for edition,tag in ((915,'915stepfinal'),(925,'925final')):
                directory = a.traces/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{cache}-pair'
                result['replays'][f'{phase}-{cache}-{edition}'] = replay(directory,tag,edition)
    # Keep each [VBlank, scanline, PPU port, byte count] together in the report.
    formatted = json.dumps(result, indent=2)
    print(re.sub(r'\[\s*(\d+(?:,\s*\d+)+)\s*\]',
                 lambda m: '[' + ', '.join(re.findall(r'\d+', m[1])) + ']', formatted))
