# SPDX-License-Identifier: MIT
"""Post-SEAL unused-pattern gap lifetime and descriptor cost oracle.

Private recorded inputs; no product implementation or CPU timing assertion.
"""
from pathlib import Path
import argparse
import csv
import json
from nes_delta231 import BASE, ROOT, sha
from analyze_nes_geometry230 import packets
from analyze_nes_schedule247 import read, ordered_patterns


def slot_range(slot):
    return (slot*16, 16) if slot < 1024 else (16384+(slot-1024)*32, 32)


def minimum_charge(plans):
    """Independent O(n^2) partition oracle, not proposed runtime code.

    Every descriptor begins/ends on a received slot, stays in one kind and
    spans <=4096B. Gaps of ANY length are allowed, including >96B. Thus this
    is a lower bound for this fixed write-set/size+96 descriptor model.
    """
    total = 0
    for kind in (0, 1):
        pp = sorted((slot*size, size) for k, slot, size in plans if k == kind)
        dp = [0]+[10**9]*len(pp)
        for end in range(1, len(pp)+1):
            for start in range(end-1, -1, -1):
                size = pp[end-1][0]+pp[end-1][1]-pp[start][0]
                if size > 4096:
                    break
                dp[end] = min(dp[end], dp[start]+size+96)
        total += dp[-1]
    return total


def analyze(prior_path, schedule_path, observer):
    prior, schedule = read(prior_path), read(schedule_path)
    assert prior['passed'] and schedule['passed']
    pins = {}
    for p in (prior_path, schedule_path):
        pins[p.relative_to(BASE).as_posix()] = sha(p)
    for name, digest in schedule['input_hashes'].items():
        assert sha(BASE/name) == digest, name
        pins[name] = digest
    manifest = read(BASE/'probes/nes-sparse232/manifest.json')['files']
    # Different arbitrary WRAM and VRAM values, independently by bank/address.
    shadows = [[bytearray((i*37+b*53+seed)&255 for i in range(20480))
                for b in range(2)] for seed in (0, 91, 218)]
    vrams = [[bytearray((i*19+b*71+seed)&255 for i in range(20480))
              for b in range(2)] for seed in (17, 120, 231)]
    valid = [set(), set()]
    ever_gap = [set(), set()]
    awaiting_write = [set(), set()]
    first_gap = {}
    later_written = set()
    later_used = set()
    first_repair = None
    rows = []
    byte_checks = 0
    for old in prior['rows']:
        f, target, gen = old['frame'], old['bank'], old['generation']
        obs = observer/f'frame{f}'
        plans = [tuple(map(int, line.split(','))) for line in obs.with_suffix('.plans').read_text().splitlines()]
        bp = BASE/f'probes/nes-sparse232/scroll02/run/bank-{gen}.bin'
        assert sha(bp) == manifest[f'scroll02/run/bank-{gen}.bin']['sha256']
        expected = bp.read_bytes()
        seal = list(packets(obs.with_suffix('.packets').read_bytes()))[-1]
        assert seal[0] == 3 and len(seal) == 238
        used = {i for i in range(1152) if seal[40+i//8] >> (i%8) & 1}
        written = {slot+(1024 if kind else 0) for kind, slot, _ in plans}
        before_valid = set(valid[target])
        repairs = awaiting_write[target] & written
        for slot in repairs:
            later_written.add((target, slot))
        awaiting_write[target] -= written
        for slot in written:
            at, n = slot_range(slot)
            for s in shadows:
                s[target][at:at+n] = expected[at:at+n]
        valid[target] |= written
        assert used <= valid[target], (f, 'coverage')
        assert not used & awaiting_write[target], (f, 'gap cannot initialize')
        for slot in used & ever_gap[target]:
            assert (target, slot) in later_written
            later_used.add((target, slot))
        if first_repair is None and repairs & used:
            slot = min(repairs & used)
            # Real future-use frame: suppress this first actual write.
            missing = before_valid | (written-{slot})
            assert not used <= missing
            first_repair = dict(frame=f, gap_frame=first_gap[(target, slot)],
                                suppressed_write_coverage_rejected=True)
        # Coverage implies every non-valid slot is unused. This implication
        # removes the need for another per-gap SEAL bitmap check/state.
        assert not (set(range(1152))-valid[target]) & used
        joined, gaps, _ = ordered_patterns(plans, set(range(1152)), 96)
        invalid = set()
        for kind, start, count in gaps:
            size, offset = (16, 0) if kind == 0 else (32, 1024)
            invalid |= {offset+i for i in range(start//size, (start+count)//size)}-valid[target]
        assert not invalid & used
        for slot in invalid:
            first_gap.setdefault((target, slot), f)
        ever_gap[target] |= invalid
        awaiting_write[target] |= invalid
        inactive_snapshots = [bytes(v[1-target]) for v in vrams]
        validity_snapshot = set(valid[target])
        for kind, start, count in joined:
            at = start+(16384 if kind else 0)
            assert 0 < count <= 4096
            for s, v in zip(shadows, vrams):
                v[target][at:at+count] = s[target][at:at+count]
        assert valid[target] == validity_snapshot  # DMA never calls mark212
        assert inactive_snapshots == [bytes(v[1-target]) for v in vrams]
        for slot in used:
            at, n = slot_range(slot)
            for v in vrams:
                assert v[target][at:at+n] == expected[at:at+n], (f, slot)
                byte_checks += n
        before = sum(old['snes']['upload'][k]['charge'] for k in ('bg', 'obj'))
        charge = sum(n+96 for _, _, n in joined)
        optimum = minimum_charge(plans)
        assert optimum <= charge
        models = {name:old['p1_models'][name]['total_charge_model']+charge-before
                  for name in ('batched16', 'causal_words')}
        rows.append(dict(frame=f, phase=old['phase'], gap_bytes=sum(n for _,_,n in gaps),
                         gap_spans=len(gaps), invalid_unused_gap_slots=len(invalid),
                         first_actual_write_after_gap=len(repairs),
                         pattern_descriptors=len(joined), pattern_charge=charge,
                         independent_min_pattern_charge=optimum,
                         models=models, scan_received_bytes=144, scan_slot_upper_bound=1152))
    assert first_repair is not None
    # Small policy counterexamples, explicitly not implementation tests.
    v = {1024, 1026}; u = {1024, 1026}
    assert u <= v and 1025 not in v
    assert not (u | {1025}) <= v  # later use without actual write
    assert not u <= set()        # STOP/common reset invalidates both bases
    assert not u <= {1024}       # other bank cannot lend validity
    assert not u <= (v-{1026})   # missing mandatory current write
    # Promoting the hole would defeat coverage; differing poison exposes it.
    assert (u | {1025}) <= (v | {1025}) and shadows[0][0] != shadows[1][0]
    warm = rows[2:]
    assert all(r['pattern_charge'] == r['independent_min_pattern_charge'] for r in warm)
    return dict(stage=247, passed=True, scope=__doc__, frames=len(rows), rows=rows,
                poison_initializations=3, used_pattern_byte_checks=byte_checks,
                used_pattern_bytes_per_initialization=byte_checks//3,
                gap_bytes=sum(r['gap_bytes'] for r in rows), gap_spans=sum(r['gap_spans'] for r in rows),
                unique_initially_invalid_gapped_bank_slots=sum(map(len,ever_gap)),
                later_actually_written_bank_slots=len(later_written),
                later_used_after_write_bank_slots=len(later_used),
                still_unwritten_at_window_end=sum(map(len,awaiting_write)),
                actual_future_use_missing_write_negative=first_repair,
                policy_counterexamples=5,
                warm_greedy_equals_independent_partition_minimum=True,
                models={name:dict(max_charge=max(r['models'][name] for r in warm),
                                  over4192=[r['frame'] for r in warm if r['models'][name]>4192])
                        for name in ('batched16','causal_words')},
                runtime_boundary=dict(existing_received_bitmap_bytes=144,
                    extra_gap_validity_state_bytes=0, existing_descriptor_bytes=8,
                    existing_descriptor_capacity=1536, bitmap_scan_slots_max=1152,
                    existing_body_bytes=3910, existing_body_capacity=3936,
                    replacement_code_bytes=None, replacement_cpu_cycles=None,
                    note='No extra validity state required by the proof. Scheduler temporaries/code/time still unimplemented.'),
                selected_implementation=None, new_65816_execution=False, physical_fps=False,
                input_hashes=pins, analyzer_sha256=sha(Path(__file__)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior', type=Path, required=True)
    p.add_argument('--schedule', type=Path, required=True)
    p.add_argument('--observer', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    result = analyze(a.prior.resolve(), a.schedule.resolve(), a.observer.resolve())
    raw = a.out/'result.json'
    raw.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    public = {k:v for k,v in result.items() if k not in ('rows','input_hashes')}
    public['residual_rows'] = [r for r in result['rows'] if r['frame'] in (952,954,955,963,968)]
    public['input_count'] = len(result['input_hashes'])
    public['private_result_sha256'] = sha(raw)
    public['evidence_sha256'] = {k:v for k,v in result['input_hashes'].items()
                               if k.endswith(('result.json','manifest.json')) or '/tools/' in k}
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    flat = [{**{k:v for k,v in r.items() if k != 'models'},**r['models']} for r in result['rows']]
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w = csv.DictWriter(f,fieldnames=list(flat[0]),lineterminator='\n');w.writeheader();w.writerows(flat)
    print(json.dumps({k:v for k,v in public.items() if k not in ('evidence_sha256','residual_rows')},indent=2))


if __name__ == '__main__':
    main()
