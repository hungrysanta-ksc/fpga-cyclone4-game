"""Summarize both physical runs, preserving exact and workload-only matches."""
import hashlib
import json
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean

from read_nes_frame900 import compare, read_trace


def analyze(folder):
    result = {}
    traces = []
    for edition in (900, 901):
        files = {kind: folder / f'nes-{kind}-mmc{edition}.{ext}' for kind, ext in
                 [('frame', 'bin'), ('game-last', 'txt'), ('budget', 'txt'), ('progress', 'txt')]}
        trace = read_trace(files['frame'])
        assert trace['edition'] == edition and trace['mode'] == 0
        traces.append(trace)
        def fields(kind):
            return dict(line.split('=', 1) for line in files[kind].read_text().splitlines() if '=' in line)
        budget, game = fields('budget'), fields('game-last')
        progress = files['progress'].read_text()
        displays = list(map(int, budget['display_1_30_60'].split(',')))
        recovery = ['verified', 'run_passed', 'stop_ok', 'base_restored', 'safe_to_reload']
        assert all(game[k] == '1' for k in recovery)
        assert all('stage=' + k in progress for k in ('STOP_DONE', 'BASE_DONE', 'MENU_PREPARED'))
        entry = dict(hashes={k: hashlib.sha256(f.read_bytes()).hexdigest() for k, f in files.items()},
                     displays=displays, fps=[round(n/d, 3) for n, d in zip(displays, (29, 30))],
                     failed_transfers=int(budget['failed_transfers']), dropped=trace['dropped'],
                     invalid=sum('invalid' in r for r in trace['rows']), windows={},
                     session={k: game[k] for k in recovery + ['run_error', 'run_rom_error',
                              'trace_aborts', 'native_receiver_error', 'native_sink_error', 'plan_error']})
        result[str(edition)] = entry
        for window in (30, 55):
            rows = [r for r in trace['rows'] if r['window'] == window and 'invalid' not in r]
            stages = {}
            for a, b in [('previous_show', 'SEAL'), ('SEAL', 'DMA_end'), ('DMA_end', 'show'),
                         ('show', 'ACK'), ('ACK', 'E0')]:
                stages[a+'--'+b] = round(mean(mean(r['elapsed_ms'][b])-mean(r['elapsed_ms'][a])
                                               for r in rows), 3)
            entry['windows'][window] = dict(count=len(rows), stage_mean_ms=stages,
                ack_to_e0_at_least_4ms=sum(r['elapsed_ms']['E0'][0]-r['elapsed_ms']['ACK'][1]>=4 for r in rows),
                display_gaps=dict(sorted(Counter(r['VBlanks'] for r in rows).items())))
    pairs = compare(*traces)
    result['exact_pairs'] = pairs['paired']
    result['unique_workload_only'] = pairs['unique_workload_only']
    result['longest_workload_runs'] = []
    for window in (30, 55):
        x, y = [[r for r in t['rows'] if r['window'] == window and 'invalid' not in r] for t in traces]
        a, b = [[tuple(r[k] for k in ('bank', 'map', 'OBJ', 'BG')) for r in rows] for rows in (x, y)]
        i, j, size = SequenceMatcher(None, a, b, autojunk=False).find_longest_match()
        assert size and all(sum(s[k:k+size] == a[i:i+size] for k in range(len(s))) == 1 for s in (a, b))
        def sample(rows, start):
            selected = rows[start:start+size]
            assert selected[-1]['generation']-selected[0]['generation'] == size-1
            return dict(generations=[r['generation'] for r in selected],
                        gaps=[r['VBlanks'] for r in selected],
                        elapsed_ms=[r['elapsed_ms'] for r in selected],
                        previous_ACK_to_E0_ms=[round(mean(rows[k-1]['elapsed_ms']['E0'])-
                            mean(rows[k-1]['elapsed_ms']['ACK']), 3) if k and
                            rows[k-1]['generation']+1 == rows[k]['generation'] else None
                            for k in range(start,start+size)])
        result['longest_workload_runs'].append(dict(window=window, work=a[i:i+size],
            MMC900=sample(x,i), MMC901=sample(y,j)))
    return result


if __name__ == '__main__':
    print(json.dumps(analyze(Path(sys.argv[1])), indent=2))
