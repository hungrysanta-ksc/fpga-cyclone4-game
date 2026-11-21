"""Compare the physical MMC903 trace to the earlier two physical recordings."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median

from read_nes_frame900 import read_trace
from read_nes_tile903 import decode


def work(row):
    return tuple(row[k] for k in ('bank', 'map', 'OBJ', 'BG'))


def runs(a, b):
    matches = []
    for i, left in enumerate(a):
        for j, right in enumerate(b):
            length = 0
            while i + length < len(a) and j + length < len(b):
                x, y = a[i + length], b[j + length]
                if (work(x) != work(y) or x['generation'] != left['generation'] + length
                        or y['generation'] != right['generation'] + length):
                    break
                length += 1
            if length:
                matches.append(dict(count=length, generations=[left['generation'], right['generation']],
                                    intervals=[sum(r['VBlanks'] for r in seq[start:start + length])
                                               for seq, start in ((a, i), (b, j))]))
    return matches


def analyze(folder):
    hashes, summary, rows = {}, {}, {}
    for n in (900, 901, 903):
        files = {k: folder / f'nes-{k}-mmc{n}.{ext}' for k, ext in
                 [('frame', 'bin'), ('game-last', 'txt'), ('budget', 'txt'), ('progress', 'txt')]}
        hashes[n] = {k: hashlib.sha256(f.read_bytes()).hexdigest() for k, f in files.items()}
        game, budget = [dict(line.split('=', 1) for line in files[k].read_text().splitlines()
                             if '=' in line) for k in ('game-last', 'budget')]
        trace = decode(files['frame']) if n == 903 else read_trace(files['frame'])
        assert trace['mode'] == 0 and not any(trace['dropped'])
        rows[n] = [r for r in trace['rows'] if 5500 <= r['tick'] < 6000]
        assert all('invalid' not in r for r in rows[n])
        displays = list(map(int, budget['display_1_30_60'].split(',')))
        assert all(game[k] == '1' for k in ('verified', 'run_passed', 'stop_ok', 'base_restored', 'safe_to_reload'))
        progress = files['progress'].read_text()
        stages = [progress.index('stage=' + k + ' ') for k in ('STOP_DONE', 'BASE_DONE', 'MENU_PREPARED')]
        assert stages == sorted(stages)
        summary[n] = dict(displays=displays, fps=[round(v / d, 4) for v, d in zip(displays, (29, 30))],
                          failed_transfers=int(budget['failed_transfers']), late_rows=len(rows[n]),
                          session={k: game[k] for k in ('run_error', 'run_rom_error', 'native_sink_error',
                                   'sink_window_error', 'trace_aborts', 'profile_last_display_tick')})
    sample = rows[903]
    tile = [r for r in sample if 'token' in r]
    def stats(values):
        return {f.__name__: round(f(values), 3) for f in (min, median, mean, max)}
    durations = {stage: stats([r['adjacent_ms'][i] for r in tile])
                 for i, stage in enumerate(('ready-visible', 'visible-E8', 'E8-E1', 'E1-head', 'head-show'))}
    durations['ready-head'] = stats([r['from_previous_show_ms']['head'] - r['from_previous_show_ms']['ready']
                                     for r in tile])
    matches = runs(rows[901], sample)
    longest = max(m['count'] for m in matches)
    skipped = {n: [dict(previous=x['generation'], next=y) for x, y in zip(seq, seq[1:])
                   if y['generation'] != x['generation'] + 1] for n, seq in rows.items()}
    return dict(hashes=hashes, runs=summary, tile_types=Counter(r['kind'] for r in tile),
                durations_ms=durations, longest_901_903=[m for m in matches if m['count'] == longest],
                target_pairs=[m for m in matches if m['generations'][0] == 1001],
                generation_discontinuities=skipped, trace903=sample)


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(json.dumps(analyze(Path(sys.argv[1])), indent=2) + '\n', encoding='utf-8')
