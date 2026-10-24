# SPDX-License-Identifier: MIT
"""Reconcile selected328 schedules with325 area; budgets are NOT measurements."""
import csv
import json
import re
from nes_delta231 import BASE, ROOT, sha


def main():
    pins = {}

    def read(path):
        pins[str(path)] = sha(path)
        return path.read_text(encoding='utf-8-sig')

    prior = json.loads(read(ROOT / 'analysis/joint328-verification.json'))
    area = json.loads(read(ROOT / 'analysis/budget326-verification.json'))
    assert prior['passed'] and area['passed']
    d = BASE / 'probes/nes-joint328'
    rows = []
    for tag in ('arm-fixed01', 'arm-window01', 'arm-normal01'):
        q = d / tag
        result = json.loads(read(q / 'result.json'))
        assert result['passed']
        assert pins[str(q / 'result.json')] == prior['pins'][str(q / 'result.json')]
        for name, digest in result['rtl_hashes'].items():
            read(q / name)
            assert pins[str(q / name)] == digest
        tb = read(q / 'joint266_tb.sv')
        assert sha(q / 'joint266_tb.sv') == result['tb_sha256']
        assert '#22.727 clk=~clk' in tb
        assert 'romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3' in tb
        assert 'core_ready267&&romcycle267%120==3' in tb
        events = list(csv.reader(read(q / 'joint-events.csv').splitlines()))
        assert pins[str(q / 'joint-events.csv')] == prior['pins'][str(q / 'joint-events.csv')]
        read(q / 'nes_native289.c')
        for old in prior['runs'][tag]['rows']:
            e = [x for x in events if len(x) > 1 and x[1] == str(old['frame'])]

            def first(name, kind=None):
                return next(x for x in e if x[0] == name and (kind is None or x[2] == str(kind)))

            req = first('firstreq305', 0)
            cycle = int(req[3])
            request_ms = int(req[-1]) / 1e9
            start_cycle = old['start_ROM_cycle']
            # Timestamped cycle is incremented in the monitoring always block.
            # Qualification uses combinational pre-edge cycle: report +/-1 cycle,
            # not a falsely exact last legal issue edge.
            previous_close = (cycle // 357368 - 1) * 357368 + 354640
            next_open = (cycle // 357368) * 357368 + 330088
            restricted = tag != 'arm-normal01'
            assert not restricted or cycle % 357368 < 330088
            accepts = old['first_ROM_accept_ms']
            last_consume = old['last_consume_ms']
            tile_consumes = [int(x[-1]) / 1e9 for x in e if x[0] == 'consume293' and x[2] == '1']
            map_consumes = [int(x[-1]) / 1e9 for x in e if x[0] == 'consume293' and x[2] == '2' and int(x[3]) >= 128]
            # Explicitly bind current warm token domain; do not infer arbitrary
            # future traces' command types from token size.
            partition = None
            if old['frame'] == 907:
                assert len(tile_consumes) == 3 and len(map_consumes) == 7
                points = [accepts, tile_consumes[-1], map_consumes[0], map_consumes[-1], last_consume, old['finish_ms']]
                assert points == sorted(points)
                partition = dict(zip(('ROM_to_last_tile_consume', 'tile_to_first_map_consume',
                    'map_consume_span', 'map_to_last_ordinary_consume', 'final_tail'),
                    [b-a for a, b in zip(points, points[1:])]))
                assert abs(sum(partition.values()) - (old['finish_ms']-accepts)) < 1e-9
            rows.append(dict(run=tag, frame=old['frame'], start_ms=old['start_ms'],
                start_ROM_cycle=start_cycle, request_cycle=cycle, request_ms=request_ms,
                request_wait_ms=accepts-request_ms, accept_ms=accepts,
                response_latency_ms=old['first_ROM_response_ms']-accepts,
                request_to_start_ms=request_ms-old['start_ms'], total_ms=old['total_ms'],
                gap_ms=old['gap_ms'], finish_ms=old['finish_ms'],
                previous_window_close_cycle=previous_close if restricted else None,
                previous_window_closed_before_start_ms=(start_cycle-previous_close)*45.454/1e6 if restricted else None,
                request_late_for_previous_window_ms=(cycle-previous_close)*45.454/1e6 if restricted else None,
                next_window_open_cycle=next_open if restricted else None,
                accept_after_nominal_open_ms=accepts-(request_ms+(next_open-cycle)*45.454/1e6) if restricted else None,
                window_boundary_uncertainty_ms=45.454/1e6 if restricted else None,
                post_ROM_ms=old['finish_ms']-accepts,
                post_ROM_budget_ms=old['finish_ms']-accepts-old['gap_ms'],
                free_entire_tail_gap_ms=old['fixed_schedule_free_tail_gap_ms'],
                partition_ms=partition, ARM_instructions=old['ARM_instructions'],
                SPI_bytes=old['SPI_bytes'], max_credit=old['max_credit']))

    board = BASE / 'probes/nes-expand325/board02'
    report = read(board / 'output_files/board.map.rpt')
    assert pins[str(board / 'output_files/board.map.rpt')] == area['pins'][str(board / 'output_files/board.map.rpt')]
    nodes = {}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c = [v.strip() for v in line.split(';')]
        if len(c) > 12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)', c[2]):
            nodes[c[10]] = int(re.search(r'\((\d+)\)', c[2])[1])
    assert nodes == area['own_entity_comb'] and sum(nodes.values()) == 17802
    for name in ('nes_mux260.sv', 'nes_validator278.sv', 'nes_spi270.sv', 'nes_queue260.sv',
                 'nes_core257.sv', 'nes_transport257.sv', 'nes_plan_batch206.sv', 'nes_plan_spi200.sv', 'nes_joint257.sv'):
        read(board / name)
    budgets = dict(host_validator=2100, queue_SPI=600, source=1100, plan=310)
    assert sum(budgets.values()) == 4110
    whole_budget = 11170 + sum(budgets.values())
    assert whole_budget == 15280 and 15408-whole_budget == 128
    warm = next(x for x in rows if x['run'] == 'arm-window01' and x['frame'] == 907)
    assert warm['previous_window_closed_before_start_ms'] > 1.74
    metadata_path = d / 'arm-window01/metadata317.json'
    metadata = json.loads(read(metadata_path))
    assert pins[str(metadata_path)] == prior['pins'][str(metadata_path)]
    profiles = {}
    for name in ('tiles290', 'next_step286', 'prepare_slice309', 'issue_map327'):
        calls = [x for x in metadata if x['name'] == name and x['start']['generation'] == 3]
        after = [x for x in calls if x['start']['modeled_ns']/1e6 >= warm['accept_ms']]
        crossing = [x for x in calls if x['start']['modeled_ns']/1e6 < warm['accept_ms'] < x['end']['modeled_ns']/1e6]
        instructions = sum(x['end']['instruction']-x['start']['instruction'] for x in after)
        profiles[name] = dict(calls=len(calls), entirely_after_ROM_calls=len(after), crossing_ROM_calls=len(crossing),
            after_ROM_inclusive_instructions=instructions, CPI1_ms=instructions/84000,
            caveat='Inclusive call counters, possibly nested/IRQ/serializer work; not additive or removable time.')
    time_budgets = dict(ROM_to_last_tile_consume=.90, tile_to_first_map_consume=.40,
        map_consume_span=.28, map_to_last_ordinary_consume=1.30, final_tail=.30)
    target_post = sum(time_budgets.values())
    assert abs(target_post-3.18) < 1e-9
    read(ROOT / 'tools/analyze_nes_budget329.py')
    out = dict(stage=329, passed=True, scope='reanalysis_only_no_new_RTL_ARM_CPU_MAP',
        selected='325 RTL +327 early manifest ARM, independently verified328', rows=rows,
        whole=prior['ARM_only_whole'], current_groups=area['groups'], design_comb_caps=budgets,
        design_caps_are_not_synthesis_estimates=True, outside_comb=11170,
        whole_design_cap=whole_budget, whole_target=15408, comb_deficit=2394,
        design_post_ROM_caps_ms=time_budgets, design_total_post_ROM_ms=target_post,
        design_gain_required_ms=warm['post_ROM_ms']-target_post,
        design_total_if_other_intervals_unchanged_ms=warm['total_ms']-(warm['post_ROM_ms']-target_post),
        design_margin_ms=warm['post_ROM_budget_ms']-target_post,
        new_measured_time_gain_ms=None, new_measured_comb_gain=None,
        phase_caveat='Window comes from restricted testbench; +/-1 monitoring cycle. Not a physical worst-case bound.',
        warm_ARM_profiles=profiles,
        pins=pins)
    (ROOT / 'analysis/budget329-verification.json').write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(passed=True, schedules=len(rows), restricted_warm=warm,
        area_design_cap=whole_budget, time_design_margin_ms=out['design_margin_ms']), indent=2))


if __name__ == '__main__':
    main()
