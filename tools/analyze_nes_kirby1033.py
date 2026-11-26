"""Compare nearby MMC1027 foreground reads with the same recorded output workload."""
import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

from read_nes_display1010 import MS, decode_rows
from read_nes_ingress1029 import boundaries


FIELDS = ('BG', 'OBJ', 'map', 'tiles', 'chunks', 'descriptor_kind', 'length_bytes', 'offset_bytes')


def workload(row):
    desc = bytes.fromhex(row['descriptor_hex'])
    return (row['BG'], row['OBJ'], row['map'], row['tiles'], row['chunks'],
            desc[1], int.from_bytes(desc[2:4], 'little'), int.from_bytes(desc[4:6], 'little'))


def measurements(row, timing):
    stamps = row['last_slot_run']['ticks_from_first_E9']
    first = round(timing['previous_show_to_first_E9_ms'] / MS)
    prev = row['previous_show']
    seal = row['SEAL'] - prev
    writer = first + stamps['writer']
    show = row['show'] - prev
    ack = row['final_ACK'] - prev
    ordered = [0, first, first + stamps['plan'], writer, seal, show, ack]
    intervals = [b-a for a,b in zip(ordered, ordered[1:])]
    if min(intervals) < 0 or sum(intervals) != ack:
        raise ValueError('inconsistent timeline')
    return dict(generation=row['generation'], time_s=row['tick']/100, bank=row['bank'],
                previous_show_to_ACK_ticks=ack, previous_show_to_show_ticks=show,
                stage_ticks=dict(zip(('to_first_E9','to_last_plan','to_writer','to_SEAL','to_show','to_ACK'),intervals)),
                request_to_first_grant_ticks=stamps['first_grant']-stamps['first_request'],
                first_grant_to_done_ticks=stamps['done']-stamps['first_grant'],
                done_to_writer_ticks=stamps['writer']-stamps['done'],
                previous_show_to_input_complete_ms=timing['previous_show_to_input_complete_ms'],
                input_complete_to_first_E9_ms=timing['input_complete_to_first_E9_ms'])


def analyze(path):
    data = path.read_bytes()
    decoded = decode_rows(data, 1027, 80)
    qualified = []
    for i,row in enumerate(decoded['rows']):
        if not row.get('last_slot_run', {}).get('foreground_read'):
            continue
        timing = boundaries(data, i, row, 1027)
        if timing:
            qualified.append((row, timing))
    pairs = []
    for (r,a),(s,b) in combinations(qualified, 2):
        if not 0 < s['tick']-r['tick'] <= 200 or workload(r) != workload(s):
            continue
        # Allow for quantization of the displayed spacing at each endpoint.
        if abs(r['spacing_ms']-s['spacing_ms']) < 16-2*MS:
            continue
        pairs.append(dict(workload=dict(zip(FIELDS, workload(r))),
                          samples=[measurements(r,a), measurements(s,b)]))
    return dict(sha256=hashlib.sha256(data).hexdigest(), samples=len(decoded['rows']),
                eligible=len(qualified), pairs=pairs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = dict(tick_ms=MS, runs=[analyze(p) for p in args.files])
    report = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.out:
        args.out.write_text(report, encoding='utf-8')
    else:
        print(report, end='')
