"""Read-only evidence audit for PR130; no new hardware validation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = (267, 268, 287, 289, 295, 297, 298)
data = {}
pins = {}
for stage in STAGES:
    path = ROOT / f"analysis/joint{stage}-verification.json"
    raw = path.read_bytes()
    data[stage] = json.loads(raw)
    assert data[stage]['passed']
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()

latest = data[298]
areas = {
    '267': data[267]['MAP']['replacement266'],
    '268': data[268]['MAP']['cleanup268'],
    '287_289': data[289]['whole_MAP'],
    '298': latest['whole_MAP'],
}
comparisons = []
for mode in ('normal', 'restricted'):
    before = {row['frame']: row for row in data[289][mode]}
    for row in latest[mode]:
        old = before[row['frame']]
        assert abs(row['source_ms'] - old['source_ms']) < 1e-9
        comparisons.append(dict(mode=mode, frame=row['frame'], before289_ms=old['total_ms'],
                                final298_ms=row['total_ms'], delta_ms=row['total_ms']-old['total_ms']))
result = dict(scope='Existing evidence audit; not new simulation, MAP, FIT, STA or physical timing',
              implementation_head='c0a68362e3c6fa1cb3d336bc69c4445e0ebdb3ca',
              whole_MAP_history=areas,
              whole_MAP_deltas={key: {metric: areas['298'][metric]-value[metric] for metric in value}
                                for key,value in areas.items() if key != '298'},
              comparable_native_schedule_289_to298=comparisons,
              latest_comb_deficit=latest['whole_MAP']['comb']-15408,
              latest_restricted907_excess_ms=latest['restricted'][2]['total_ms']-1000/60,
              input_sha256=pins)
out = ROOT / 'analysis/pr130-retrospective.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding='utf-8', newline='\n')
print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'},ensure_ascii=False,indent=2))
