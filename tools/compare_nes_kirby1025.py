"""Compare two Kirby traces within the same 400 ms frame-start interval."""
import argparse
import json
from pathlib import Path

from read_nes_tail1012 import HEADER, MS, decode


def read_run(path):
    data = path.read_bytes()
    if HEADER.unpack_from(data)[2] != 0:
        raise ValueError('select the two normal MMC3 runs')
    trace = decode(data, 1025)
    rows = {}
    for row in trace['rows']:
        if 'invalid' in row:
            continue
        slot = row['tick'] // 40
        if slot in rows:
            raise ValueError('duplicate sampling interval')
        rows[slot] = row
    return rows, dict(recorded=len(trace['rows']), qualified=len(rows), dropped=trace['dropped'],
                      displays_55_60=trace['displayed55'])


def stages(row):
    return dict(
        previous_show_to_seal_ms=(row['SEAL'] - row['previous_show']) * MS,
        # Negative when the last observed DMA write preceded SEAL.
        seal_to_last_dma_write_ms=(row['last_DMA'] - row['SEAL']) * MS,
        last_dma_write_to_show_ms=row['dma_to_show_ms'],
        show_to_final_ack_ms=(row['final_ACK'] - row['show']) * MS,
        spacing_ms=row['spacing_ms'])


def compare(first, second):
    a, summary_a = read_run(first)
    b, summary_b = read_run(second)
    pairs = []
    for slot in sorted(a.keys() & b.keys()):
        x, y = a[slot], b[slot]
        fields = ('BG','OBJ','map','tiles','chunks')
        # Compare exact observable work first. Declare near matches separately.
        delta = tuple(abs(x[k]-y[k]) for k in fields)
        if any(d>limit for d,limit in zip(delta,(8,1,1,0,0))):
            continue
        sx, sy = stages(x), stages(y)
        pairs.append(dict(match='near' if any(delta) else 'exact',
                          ticks=[x['tick'],y['tick']], generation=[x['generation'],y['generation']],
                          workload=[{k:r[k] for k in fields} for r in (x,y)],
                          stage_ms=[sx,sy], delta_ms={k:sy[k]-sx[k] for k in sx}))
    return dict(runs=[summary_a,summary_b], shared_slots=len(a.keys() & b.keys()), pairs=pairs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.first,args.second), indent=2))
