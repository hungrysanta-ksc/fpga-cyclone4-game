"""PR131 retrospective: recompute archived costs and audit integration boundaries.

No new performance, synthesis, firmware or hardware run. The separate join
probe reproduces two admission failures using unchanged source/lease modules.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
PINS = {}


def read(path):
    path = Path(path)
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return data.decode('utf-8')


def data(name):
    return json.loads(read(ROOT / 'analysis' / name))


def row(result, run, frame=907):
    return next(x for x in result['runs'][run]['rows'] if x['frame'] == frame)


def main():
    old = data('pr130-retrospective.json')
    ingress = data('ingress338-verification.json')
    raw = data('raw352-verification.json')
    raster = data('raster355-verification.json')
    host = data('prefetch359-verification.json')
    fast = data('execute362-verification.json')
    abi = data('abi364-verification.json')
    actual_read = data('read336-verification.json')
    maps = {'298': old['whole_MAP_history']['298'], '338': ingress['whole'],
            '359': host['host_whole'], '362': fast['maps']['objmap01']}
    assert maps['362'] == abi['whole_reference']
    limit = abi['budget']['device_limit']
    assert limit == 15408
    deltas = {k: {f: v[f] - maps['298'][f] for f in maps['298']} for k, v in maps.items()}
    deficits = {k: v['comb'] - limit for k, v in maps.items()}
    assert deltas['359']['comb'] == -470 and deltas['362']['comb'] == 41
    assert actual_read['whole']['comb'] == 17378
    assert maps['338']['comb'] == 17274

    probe = BASE / 'probes/nes-pr131-review/join02'
    join = json.loads(read(probe / 'result.json'))
    assert join['passed']
    for path, expected in join['pins'].items():
        read(path)
        assert PINS[path] == expected, path
    for case in range(3):
        log = read(probe / f'case{case}.log')
        assert 'Errors: 0, Warnings: 0' in log
        assert ('REPRO131' if case < 2 else 'CONTROL131') in log
    read(ROOT / 'tools/probe_nes_pr131_join.py')
    mapdir = BASE / 'probes/nes-execute362/objmap01'
    wrapper = read(mapdir / 'nes_live_joint.sv')
    lease = read(mapdir / 'nes_capture_lease201.sv')
    collector = read(mapdir / 'nes_native_frame201.sv')
    planes = read(mapdir / 'nes_native_planes165.sv')
    assert 'resource-only' in wrapper
    assert '.content_epoch(captured_epoch204)' in wrapper
    assert '.frame_generation(captured_gen204)' in wrapper
    assert 'assign export_release204=source_done267;' in wrapper
    assert '!fetch_owned && !owned && ppu_ce && scanline==7 && dot==257' in collector
    assert 'wire end_frame=active && ppu_ce && scanline==232 && dot==1;' in planes

    traces = {}
    for run in ('keepwindow01', 'keepfixed01'):
        folder = BASE / 'probes/nes-execute362' / run
        tb = read(folder / 'joint266_tb.sv')
        assert 'wire core_req267=active263&&core_ready267&&romcycle267%120==3;' in tb
        assert 'active263=1' in tb[tb.index('task output_frame'):]
        assert 'for(t=7*341+257;t<=232*341+1;t++)begin' in tb
        loop = tb.index('for(f=first;f<=last;f++)begin')
        assert tb.index('wait(source_done);', loop) < tb.index('output_frame();', loop)
        events = [x.split(',') for x in read(folder / 'joint-events.csv').splitlines()]
        start = next(e for e in events if e[:2] == ['start319', '907'])
        done = next(e for e in events if e[:2] == ['input_done337', '907'])
        final = next(e for e in events if e[:2] == ['frame_done', '907'])
        elapsed = (int(final[2]) - int(start[2])) / 1e9  # ps -> ms
        input_ms = (int(done[3]) - int(start[2])) / 1e9
        assert abs(elapsed - row(fast, run)['total_ms']) < 1e-9
        # Generous upper bound: end-of-capture event to the next start event.
        # Excludes actual post-capture drain/start wait, so available time is less.
        budget_clocks = (262 * 341 - (232 * 341 + 1) + (7 * 341 + 257)) * 4
        assert budget_clocks == 51492
        budget_ms = budget_clocks * 45.454 / 1e6
        assert input_ms > budget_ms
        traces[run] = dict(total_ms=elapsed, source_input_ms=input_ms,
                           next_capture_upper_clocks=budget_clocks,
                           next_capture_upper_ms=budget_ms,
                           input_over_upper_ms=input_ms - budget_ms,
                           source_start_ROM_cycle=int(start[3]))

    raw_row = row(raw, 'normal02')
    normal_before = raw_row['total_ms'] - raw_row['delta_ms']
    normal_after = row(raster, 'normal01')['total_ms']
    differences = {}
    for after, before in [('keepfixed01', 'fixed01'), ('keepwindow01', 'window01')]:
        a, b = row(fast, after), row(fast, before)
        differences[after] = dict(before_ms=b['total_ms'], after_ms=a['total_ms'],
                                  delta_ms=a['total_ms'] - b['total_ms'],
                                  same_source_start_ROM_phase=a['start_ROM_cycle'] == b['start_ROM_cycle'],
                                  before_ROM_cycle=b['start_ROM_cycle'], after_ROM_cycle=a['start_ROM_cycle'])
    budget = abi['budget']
    assert budget['replace_total'] - budget['new_inclusive_cap'] == budget['required_net_deletion'] == 2471
    result = dict(
        scope=__doc__, implementation_head='6674e57c68695b67b02ee36b57fd6868ae2f9831',
        base_master='d7a96c5652d7c511d061ae5035277027c14ec597',
        whole_MAP=maps, whole_delta_vs_PR130= deltas, comb_device_limit=limit,
        comb_deficits=deficits,
        best_area_initial_shortage_recovered_percent=470 / 2275 * 100,
        retained_local_deletions={'336_read_event_comb': -271, '338_aligned_queue_comb': -104, '359_host_comb': -61},
        normal_ARM_series=dict(before_ms=normal_before, after_ms=normal_after, delta_ms=normal_after-normal_before,
                               scope='Recorded normal-service series, not PR-wide matched phase or restricted-ROM WCET.'),
        prefetch_comparisons=differences,
        fast_hint_window_margin_us=row(fast, 'keepwindow01')['fill_margin_to_initial_window_upper_ms'] * 1000,
        capture_deadline_audit=traces,
        capture_deadline_scope='Conditional audit of existing 262-line / four-NES-clock-per-dot fixture. No free-running collector simulation; source input excludes capture and post-capture wait. Actual hardware phase/cadence must be bound. Does not assert hardware FPS or add fixture capture time to latency.',
        board_join_probe=dict(passed=True, cases=3, reproduced_failures=join['original_failures_reproduced'],
                              scope=join['scope'], control=join['control']),
        untested_integration=['MAP resource wrapper source context differs from functional TB',
                             'core_req267 is zero during critical input-stage hint fill',
                             'next collector frame is driven only after preceding output_frame returns',
                             'full firmware hint foreground loop and full 65816 service are unbound',
                             'no selected candidate whole FIT/STA/physical run'],
        ABI364=dict(required_deletion_comb=2471, replace_total_comb=3314,
                    deletion_fraction_percent=2471/3314*100, remaining_cap_comb=843,
                    actual_deleted_comb=0, new_measured_cost=None,
                    status='Arithmetic allowance, not an achievable implementation demonstrated by this PR.'),
        conclusion='Keep proven component gains. Integration and sustained-capture deadline gates precede further ABI/control optimization.',
        new_performance_run=False, new_MAP=False, FIT=False, STA=False, physical=False,
        pins=PINS)
    out = ROOT / 'analysis/pr131-retrospective.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: result[k] for k in ('comb_deficits', 'normal_ARM_series', 'capture_deadline_audit')}, ensure_ascii=False, indent=2))
    print(f'PASS: archived arithmetic, join logs and static integration checks; {len(PINS)} input hashes')


if __name__ == '__main__':
    main()
