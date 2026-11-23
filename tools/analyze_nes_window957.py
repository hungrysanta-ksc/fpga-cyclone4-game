"""Compare physical MMC956 endpoints with directed RTL runs on a common grant calendar."""
import hashlib
import json
import re
import sys
from pathlib import Path

from analyze_nes_dense956 import report


def events(log, name):
    return [dict((k, int(v)) for k, v in re.findall(r'(\w+)=(-?\d+)', line))
            for line in log.splitlines() if line.startswith('# ' + name + ' ')]


def analyze(capture, directory):
    physical = report(capture)
    if physical['summary_rows'] != 120 or any(physical['dropped']):
        raise ValueError('incomplete hardware trace')
    targets = []
    for generation, token, ordinal in [(1406, 3660, 2), (1410, 3678, 4), (1410, 3678, 11)]:
        frame, = (f for f in physical['targets'] if f['generation'] == generation)
        chunk, = (c for c in frame['chunks'] if c['token'] == token)
        tile, = (t for t in chunk['requested_tiles'] if t['tile'] == ordinal - 1)
        targets.append(dict(generation=generation, token=token, ordinal=ordinal,
                            previous_bank_return_ms=chunk['previous_same_bank_return_ms'],
                            **{k: v for k, v in tile.items() if k != 'tile'}))
    runs = []
    for gap in (1, 2):
        for form in ('short', 'full'):
            for lead in (-50, 75, 1100):
                log = (directory / f'gap{gap}-{form}-lead{lead}.log').read_text()
                result, = events(log, 'RESULT957')
                fills = events(log, 'FILL957')
                if (events(log, 'PASS957') != [{'bytes': 32}] or
                    (result['gap'], result['full'], result['lead']) != (gap, int(form == 'full'), lead)
                    or result['grants'] != len(fills)):
                    raise ValueError('incomplete or stale run')
                stalled = max(fills, key=lambda e: e['grant'] - e['request'])
                result['longest_wait_grant_ordinal'] = fills.index(stalled) + 1
                result['longest_wait_event'] = stalled
                runs.append(result)
    if 'PASS914 checked repeated generation after STOP' not in (directory / 'guards.log').read_text():
        raise ValueError('missing priority, CRC, generation and STOP checks')
    return dict(baseline='MMC955', physical_edition=956, rtl='952checked', time_bin_ms=physical['time_bin_ms'],
                physical_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(), physical_tiles=targets,
                clock_ns=46.56, calendar='first two gaps of service509/fill1, only contiguous tested spans retained',
                calendar_full_sha256='80193115c8ba76322ebc602b043b3e79446e944df8bddcf17a5e2abd94e6c5c9',
                runs=runs)


if __name__ == '__main__':
    print(json.dumps(analyze(*map(Path, sys.argv[1:])), indent=2))
