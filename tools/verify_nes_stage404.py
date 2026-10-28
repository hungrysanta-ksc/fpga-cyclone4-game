# SPDX-License-Identifier: MIT
"""Compare the partial 404 experiment with the matching 402 full-path run.

No conclusion is emitted until the actual run has completed. This does not
certify the still-unimplemented common executor or raster/lease replacement.
"""
import json
from pathlib import Path

from nes_delta231 import BASE, sha
from cost_nes_joint402 import measure

root = BASE / 'probes/nes-stage404'
candidate = root / 'live01'
reference = BASE / 'probes/nes-joint402/live04'
if not (candidate / 'result.json').exists():
    raise SystemExit('Full 404 run is not complete; do not infer a PASS from a prefix.')
result = json.loads((candidate / 'result.json').read_text())
assert result['passed']
old = json.loads((reference / 'manifest402.json').read_text())
new = json.loads((candidate / 'manifest402.json').read_text())
assert old['ELF'] == new['ELF']
assert set(old['RTL']) == set(new['RTL'])
assert [k for k in old['RTL'] if old['RTL'][k] != new['RTL'][k]] == ['nes_stage396.sv']
assert (candidate / 'joint-events.csv').read_bytes() == (reference / 'joint-events.csv').read_bytes()
assert json.loads((candidate / 'arm-result.json').read_text()) == json.loads((reference / 'arm-result.json').read_text())
previous = measure(BASE / 'probes/nes-joint402/map07')
current = measure(root / 'map02')
report = {'passed': True, 'events_and_ARM_identical_to_402': True,
          'event_sha256': sha(candidate / 'joint-events.csv'),
          'ARM_image': new['ELF'], 'old_whole': previous['whole'],
          'new_whole': current['whole'],
          'delta': {k: current['whole'][k] - previous['whole'][k] for k in previous['whole']},
          'scope': 'staging stamp scratch only; VM and raster/lease unchanged',
          'independent_new_guard_tests': False, 'FIT': False, 'STA': False,
          'physical_60fps_proven': False}
(root / 'comparison404.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
print(json.dumps(report, indent=2))
