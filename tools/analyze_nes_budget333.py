# SPDX-License-Identifier: MIT
"""Reconcile immutable332 evidence; proposed caps are not measured savings."""
import csv
import json
import re
from nes_delta231 import BASE, ROOT, sha


def main():
    pins = {}

    def read(p):
        pins[str(p)] = sha(p)
        return p.read_text(encoding='utf-8-sig')

    prior = json.loads(read(ROOT / 'analysis/execute332-verification.json'))
    assert prior['passed'] and prior['comb_deficit'] == 2241

    def bound(p):
        s = read(p)
        assert pins[str(p)] == prior['pins'][str(p)], str(p)
        return s

    base = BASE / 'probes/nes-execute332'
    rows = []
    profiles = {}
    for tag in ('window03', 'fixed02', 'normal01'):
        q = base / tag
        result = json.loads(bound(q / 'result.json'))
        assert result['passed']
        for n, digest in result['rtl_hashes'].items():
            bound(q / n)
            assert pins[str(q / n)] == digest
        tb = bound(q / 'joint266_tb.sv')
        assert '#22.727 clk=~clk' in tb
        assert 'romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3' in tb
        assert 'core_ready267&&romcycle267%120==3' in tb
        for name in ('nes_native289.c', 'nes_output264.c', 'nes_refill267.c'):
            bound(q / name)
        events = list(csv.reader(bound(q / 'joint-events.csv').splitlines()))
        meta = json.loads(bound(q / 'metadata317.json'))
        for old in prior['runs'][tag]['rows']:
            f = old['frame']
            e = [x for x in events if len(x) > 1 and x[1] == str(f)]
            req = next(x for x in e if x[0] == 'firstreq305' and x[2] == '0')
            cycle = int(req[3])
            close = (cycle // 357368 - 1) * 357368 + 354640
            rows.append(dict(run=tag, frame=f, total_ms=old['total_ms'], gap_ms=old['gap_ms'],
                start_ms=old['start_ms'], start_ROM_cycle=old['start_ROM_cycle'],
                first_ROM_accept_ms=old['first_ROM_accept_ms'], request_ms=int(req[-1])/1e9,
                request_wait_ms=old['first_ROM_accept_ms']-int(req[-1])/1e9,
                request_late_for_previous_window_ms=(cycle-close)*45.454/1e6 if tag != 'normal01' else None,
                previous_window_closed_before_start_ms=(old['start_ROM_cycle']-close)*45.454/1e6 if tag != 'normal01' else None,
                post_ROM_ms=old['post_ROM_ms'], partition_ms=old['partition_ms'],
                ARM_instructions=old['ARM_instructions'], SPI_bytes=old['SPI_bytes'],
                max_credit=old['max_credit']))
            if tag == 'fixed02':
                ref = json.loads(read(ROOT / 'analysis/completion331-verification.json'))
                fixed = next(x for x in ref['runs']['fixed02']['rows'] if x['frame'] == f)
                assert old['start_ms'] == fixed['start_ms'] and old['start_ROM_cycle'] == fixed['start_ROM_cycle']
            if f != 907:
                continue
            calls = [x for x in meta if x['start']['generation'] == 3]
            prep = next(x for x in calls if x['name'] == 'prepare289')
            final = next(x for x in calls if x['name'] == 'tiles290' and x['arg'] == 1)
            h2_ins = final['start']['instruction'] - prep['end']['instruction']
            h2_ms = (final['start']['modeled_ns'] - prep['end']['modeled_ns'])/1e6
            assert abs(h2_ms - h2_ins/84000) < 1e-9
            # Boundary evidence identifies a call-site envelope, NOT a new
            # function-level PC profile. h2 is between these calls in frame_core284.
            arm_path = q / 'arm907.json'
            arm = json.loads(read(arm_path))
            assert pins[str(arm_path)] == prior['pins'][str(arm_path)]
            tx = [x for x in arm['transfers'] if x['tx']]
            first_ordinary = next(x for x in tx if bytes.fromhex(x['tx'])[:3] == bytes((0xe1, 2, 4)))
            obj_bulk = next(x for x in tx if bytes.fromhex(x['tx'])[:3] == bytes((0xe1, 7, 1)))
            rom_last_obj = [int(x[-1])/1e9 for x in e if x[0] == 'romtile305' and x[2] == '1'][-1]
            tile = [int(x[-1])/1e9 for x in e if x[0] == 'consume293' and x[2] == '1']
            assert len(tile) == 3
            funcs = {}
            for name in ('tiles290', 'bulk289', 'span', 'dirty_span231', 'prepare_map330', 'issue_metadata317'):
                a = [x for x in calls if x['name'] == name and x['start']['modeled_ns']/1e6 >= old['first_ROM_accept_ms']]
                cross = [x for x in calls if x['name'] == name and x['start']['modeled_ns']/1e6 < old['first_ROM_accept_ms'] < x['end']['modeled_ns']/1e6]
                funcs[name] = dict(wholly_after_ROM_calls=len(a), crossing_ROM_calls=len(cross),
                    inclusive_instructions=sum(x['end']['instruction']-x['start']['instruction'] for x in a))
            profiles[tag] = dict(h2_callsite_envelope_instructions=h2_ins, h2_callsite_envelope_ms=h2_ms,
                h2_envelope_scope='prepare289 return to final tiles290 entry: includes h2 and caller checks, no isolated PC trace',
                first_ordinary_pretransfer_instructions=first_ordinary['instructions'],
                first_ordinary_pretransfer_CPI1_ms=first_ordinary['instructions']/84000,
                first_ordinary_transfer_end_ms=first_ordinary['RTL_ns']/1e6,
                last_OBJ_first_output_byte_ms=rom_last_obj, OBJ_bulk_transfer_end_ms=obj_bulk['RTL_ns']/1e6,
                last_tile_consume_ms=tile[-1], last_OBJ_first_byte_to_consume_ms=tile[-1]-rom_last_obj,
                last_OBJ_first_byte_to_bulk_end_ms=obj_bulk['RTL_ns']/1e6-rom_last_obj,
                bulk_end_to_last_tile_consume_ms=tile[-1]-obj_bulk['RTL_ns']/1e6,
                function_profiles=funcs,
                caveat='Call counters are inclusive/nested; first output byte is not tile completion. No sum with wall-clock partitions or claim all work removable.')

    report = bound(base / 'board03/output_files/board.map.rpt')
    nodes = {}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c = [x.strip() for x in line.split(';')]
        if len(c) > 12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)', c[2]):
            nodes[c[10]] = int(re.search(r'\((\d+)\)', c[2])[1])
    assert nodes == prior['own_entity_comb'] and sum(nodes.values()) == 17649
    def own(suffix):
        a = [v for k,v in nodes.items() if k.endswith(suffix)]
        assert len(a) == 1
        return a[0]
    def tree(suffix):
        a = [k for k in nodes if k.endswith(suffix)]
        assert len(a) == 1
        return sum(v for k,v in nodes.items() if k == a[0] or k.startswith(a[0]+'|'))
    groups = dict(host_validator=own('nes_output260:flow')+own('nes_validator278:validator'),
        queue_SPI=own('nes_queue260:queue')+own('nes_spi270:spi_front270'),
        source=own('nes_core257:encoder')+tree('nes_transport257:transport'),
        plan=own('nes_plan_path267:retained_plan267')+tree('nes_plan_batch206:transport')+own('nes_plan_spi200:endpoint'))
    assert groups == prior['groups']
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_joint257.sv','nes_transport257.sv',
              'nes_core257.sv','nes_plan_path267.sv','nes_plan_batch206.sv','nes_plan_spi200.sv','nes_queue260.sv','nes_spi270.sv'):
        bound(base / 'board03' / n)
    caps = dict(host_validator=2100, queue_SPI=600, source=1100, plan=310)
    outside = sum(nodes.values())-sum(groups.values())
    assert outside == 11166
    area_budget = outside+sum(caps.values())
    assert area_budget == 15276
    time_caps = dict(ROM_to_last_tile=.900, tile_to_first_map=.400, map_span=.280,
                     last_map_to_last_ordinary=1.300, final_tail=.300)
    warm = next(x for x in rows if x['run']=='window03' and x['frame']==907)
    assert abs(sum(warm['partition_ms'].values())-warm['post_ROM_ms']) < 1e-9
    gain = warm['post_ROM_ms']-sum(time_caps.values())
    predicted = warm['total_ms']-gain
    # Purely arithmetic scenarios, with the measured332 outside intervals fixed.
    h = profiles['window03']['h2_callsite_envelope_ms']
    ordinary = profiles['window03']['first_ordinary_pretransfer_CPI1_ms']
    scenarios = dict(free_entire_final_tail_gap_ms=warm['gap_ms']-warm['partition_ms']['final_tail'],
        free_H2_callsite_and_first_ordinary_bundle_gap_ms=warm['gap_ms']-h-ordinary,
        source_plan_zero_comb_still_short=sum(nodes.values())-groups['source']-groups['plan']-15408,
        host_validator_only_required_reduction_percent=224100/groups['host_validator'])
    assert scenarios['source_plan_zero_comb_still_short'] == 10
    read(ROOT / 'tools/analyze_nes_budget333.py')
    out = dict(stage=333, passed=True, scope='reanalysis_and_design_contract_only_no_new_execution_or_MAP',
        baseline=332, rows=rows, profiles=profiles, whole=prior['whole'], groups=groups,
        outside_comb=outside, comb_deficit=2241, own_entity_comb=nodes,
        design_comb_caps=caps, design_reductions={k:groups[k]-caps[k] for k in groups},
        design_whole_comb=area_budget, design_comb_margin=15408-area_budget,
        maximum_group_comb_to_fit_arithmetic=15408-outside,
        design_time_caps_ms=time_caps, design_post_ROM_ms=sum(time_caps.values()),
        design_time_gain_ms=gain, design_total_if_outside_unchanged_ms=predicted,
        design_time_margin_ms=1000/60-predicted, scenarios=scenarios,
        post_ROM_cap_only_sensitivity=[dict(run=r['run'],total_ms=r['total_ms']-r['post_ROM_ms']+sum(time_caps.values()),
            gap_ms=r['total_ms']-r['post_ROM_ms']+sum(time_caps.values())-1000/60)
            for r in rows if r['frame']==907],
        ARM_state_budget_extra_bytes=32, additional_payload_buffer_bytes=0,
        additional_FPGA_RAM_bits=0, additional_M9K=0,
        caps_are_acceptance_requirements_not_estimates=True,
        new_measured_time_gain_ms=None,new_measured_comb_gain=None,FIT=False,STA=False,physical_60fps=False,
        caveats=['No inclusive parent/child area double count.',
                 'Continuous and fixed ROM phases are separate; no free previous-frame prefetch.',
                 'Same source/plan cursor already shared since319; count only further deleted control.',
                 'Independent expected/actual checks and actual SNES read/STOP/drain/final ACK/VBlank remain mandatory.',
                 'Whole MAP comb capacity arithmetic is not placement, routing, timing or board acceptance.'],pins=pins)
    (ROOT/'analysis/budget333-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(passed=True,rows=len(rows),pins=len(pins),warm=warm,
        profiles=profiles['window03'],groups=groups,area_cap=area_budget,
        time_cap=predicted,margin=out['design_time_margin_ms'],scenarios=scenarios),indent=2))


if __name__ == '__main__':
    main()
