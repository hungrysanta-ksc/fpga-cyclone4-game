# SPDX-License-Identifier: MIT
"""R0 source audit and exact decomposition of the existing conditional schedule.

No hardware execution: RTL measurements are inherited fixture measurements.
Unknown integration costs remain null, never zero or a measured time bound.
"""
from pathlib import Path
import argparse, csv, hashlib, json, math, re, shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
MASTER = 21477.270
MERGED129 = '2978f04aef65987c615d62ca54576e68fc946637'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    out = a.out.resolve()
    assert not out.exists(), 'Preserve prior runs'
    out.mkdir(parents=True)
    pins = {}

    def pin(rel):
        p = BASE / rel
        pins[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        return p

    def read(rel):
        return json.loads(pin(rel).read_text(encoding='utf-8'))

    def csvread(rel):
        with pin(rel).open(encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))

    def pub(rel):
        return ROOT.name + '/' + rel

    old250 = read('probes/nes-joint250/analysis02/result.json')
    old249 = read('probes/nes-joint249/analysis02/result.json')
    placement = read('probes/nes-wholepath247/placement05/result.json')
    joint = read(pub('analysis/joint255-verification.json'))
    # Connect private result bytes to their existing public verification records.
    for rel, public in [
        ('probes/nes-joint250/analysis02/result.json', 'analysis/joint250-verification.json'),
        ('probes/nes-joint249/analysis02/result.json', 'analysis/joint249-verification.json'),
        ('probes/nes-wholepath247/placement05/result.json', 'analysis/placement247-verification.json'),
    ]:
        v = read(pub(public))
        assert pins[rel] == v['private_result_sha256'], rel
    assert old250['passed'] and old249['passed'] and placement['passed'] and joint['passed']
    detail = {int(r['frame']): r for r in csvread(pub('analysis/joint255-frames.csv'))}
    schedules = csvread(pub('analysis/joint255-schedules.csv'))
    wire = {r['frame']: r['source_spi_bytes'] for r in old249['wire_rows'] if r['codec'] == 'block'}
    ref249 = {(r['frame'], r['map_setup_clocks']): r for r in old249['rows']
              if r['codec'] == 'block' and r['map_format'] == 'gap16_64' and r['nonmap_service_clocks'] == 500}
    ref250 = {(r['frame'], r['map_setup_clocks'], r['retained_policy']): r for r in old250['rows']}
    display = {r['frame']: r['display_sensitivity_maximum_ms'] for r in placement['rows']
               if r['placement'] == 'FPGA_typed_ext16'}
    components = {
        'source_rtl_ms': 'inherited_RTL_fixture_elapsed_includes_SPI_polling_and_waits',
        'output_spi_model_ms': 'modeled_existing_output_and_control_wire_at_2.625MHz_excludes_extra_H2',
        'service_wait_model_ms': 'derived_critical_path_wait_after_existing_SPI_overlap_not_all_CPU_work',
        'display_sample_ms': 'historical_SNES_sample_reused_by_model_excludes_VBlank_wait_not_WCET',
        'parser_allocated_ms': 'unmeasured_8_FPGA_cycles_per_output_byte',
        'final_fixed_allocated_ms': 'unmeasured_2000_SNES_master_clocks',
        'phase_allocated_ms': 'unmeasured_2_FPGA_cycles_retained_from251',
        'arm_allocated_ms': 'unmeasured_32000_ARM_cycles_at84MHz',
        'certificate_wire_allocated_ms': 'unbound_extra32B_wire_at2.625MHz',
        'receipt_nonstream_rtl_ms': 'inherited_RTL_fixture_elapsed_minus_driver_stream_not_actual_parser_or_DMA',
        'stress_stream_reservation_ms': 'artificial_driver_reservation_double_charges_transfer_not_a_bound',
    }
    rows = []
    for s in schedules:
        f, setup = int(s['frame']), int(s['setup'])
        o = ref250[f, setup, s['retained_policy']]
        prior = ref249[f, setup]
        d = detail[f]
        final = prior['final_fixed_allocated_ms']
        assert math.isclose(final, 2000 / MASTER, abs_tol=1e-12)
        # Undo only the explicitly added250 terms, then remove the old input
        # wire. The remainder is the248 event scheduler's OUTPUT critical path.
        model = o['total_ms'] - sum(o[k] for k in (
            'source_prepare_ms', 'parser_allocated_ms', 'receipt_core_ms', 'validate_ms')) - final
        model_output = model - wire[f] * 8 / 2625
        output_bytes = prior['spi_bytes'] - wire[f]
        output_wire = output_bytes * 8 / 2625
        wait = model_output - output_wire - display[f]
        assert wait >= -1e-10, (f, wait)
        r = dict(frame=f, setup=setup, retained_policy=s['retained_policy'],
                 accounting_policy=s['accounting_policy'], output_model_spi_bytes=output_bytes,
                 source_rtl_ms=int(d['source_cycles']) / 22000,
                 output_spi_model_ms=output_wire, service_wait_model_ms=wait,
                 display_sample_ms=display[f], parser_allocated_ms=o['parser_allocated_ms'],
                 final_fixed_allocated_ms=final, phase_allocated_ms=2 / 22000,
                 arm_allocated_ms=32000 / 84000, certificate_wire_allocated_ms=32 * 8 / 2625,
                 receipt_nonstream_rtl_ms=int(d['nonstream_cycles']) / 22000,
                 stress_stream_reservation_ms=(int(d['driver_stream_cycles']) / 22000
                    if s['accounting_policy'] == 'serialized_stress_reservation' else 0))
        total = sum(r[k] for k in components)
        assert math.isclose(total, float(s['total_ms']), abs_tol=1e-10), (f, total, s)
        r.update(reconstructed_conditional_ms=total, residual_all_unknown_ms=1000 / 60 - total,
                 prior255_ms=float(s['total_ms']), actual_end_to_end_ms=None)
        rows.append(r)
    assert len(rows) == 552 and {r['frame'] for r in rows} == set(range(907, 976))
    # Explicitly audit real generated sources, not names of older public modules.
    anchors = {
        'probes/nes-source240/board01/nes_live_joint.sv': [
            'nes_source240 native_source240', '.done(export_release204)', 'nes_direct206 direct_path'],
        'probes/nes-source240/board01/nes_sink_spi165.sv': [
            'buffer[0:1023]', 'wire [2:0] used=accepted[2:0]-retired[2:0]',
            'read_address=checking?', 'retired<=retired+1', 'module nes_sink_spi165'],
        'probes/nes-source240/board01/nes_direct206.sv': [
            'nes_source_tile192', 'nes_tile_bulk206', 'nes_bulk_control194', 'nes_plan_batch206'],
        'probes/nes-joint255/test03/nes_core255.sv': [
            'assign lease_ok=frame_owned&&geometry_valid&&generation==frame_generation',
            'base_serial<=serial;done<=1;', 'state<=V_IDLE',
            'assign sink_valid=', 'V_WAITDISPLAY:if(v_display_ack)'],
        'probes/nes-joint255/test03/nes_joint255.sv': [
            'frame_owned&&geometry_valid&&output_phase', 'nes_transport255 transport'],
        pub('src/nes/rtl/nes_capture_lease201.sv'): [
            'waiting_display', 'assign release_frame=stop||export_release', 'retire_commit&&!bad_retire'],
        pub('src/nes/rtl/nes_bulk_aperture188.sv'): [
            'storage[0:4095]', 'consume_token==tokens[reader]', 'sealed[reader]<=0'],
        'probes/nes-runtime233/arm01/src/nes_native_runtime165.c': [
            'nes_sink231_seal', 'if(!s->sink.displayed', 'nes_plan200_retire', 'nes_native165_consumed'],
    }
    observations = []
    for rel, needles in anchors.items():
        lines = pin(rel).read_text(encoding='utf-8').splitlines()
        for needle in needles:
            hits = [i + 1 for i, line in enumerate(lines) if needle in line]
            assert hits, (rel, needle)
            observations.append(dict(path=rel, anchor=needle, lines=hits))
    rtl = read('probes/nes-joint255/test03/result.json')['rtl_hashes']
    for name, digest in rtl.items():
        p = pin('probes/nes-joint255/test03/' + name)
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest
    report = pin('probes/nes-source240/board01/output_files/board.map.rpt').read_text()
    names = ['|nes_source240:native_source240|', '|nes_direct206:direct_path|',
             '|nes_sink_bridge165:sink|', '|nes_sink_bus165:bus|', '|nes_sink_spi165:endpoint|',
             '|nes_tile_bulk206:bulk|', '|nes_bulk_control194:control|',
             '|nes_plan_batch206:transport|', '|nes_plan_spi200:endpoint|']
    area = []
    for line in report.splitlines():
        c = [v.strip() for v in line.split(';')]
        if len(c) > 4 and c[1] in names and re.fullmatch(r'\d+ \(\d+\)', c[2]):
            area.append(dict(instance=c[1], comb=int(c[2].split()[0]), FF=int(c[3].split()[0]),
                             bits=int(c[4]), metric='old240_MAP_inclusive_hierarchy_NOT_reclaim'))
    assert len(area) == len(names)
    heavy = [952, 954, 955, 962, 963, 968, 970]
    summaries = []
    for key in sorted({(r['setup'], r['retained_policy'], r['accounting_policy']) for r in rows}):
        group = [r for r in rows if (r['setup'], r['retained_policy'], r['accounting_policy']) == key]
        worst = max(group, key=lambda r: r['reconstructed_conditional_ms'])
        summaries.append(dict(setup=key[0], retained_policy=key[1], accounting_policy=key[2],
            worst_frame=worst['frame'], maximum_ms=worst['reconstructed_conditional_ms'],
            over=[r['frame'] for r in group if r['residual_all_unknown_ms'] < 0]))
        if worst['frame'] not in heavy:
            heavy.append(worst['frame'])
    unknowns = [
        ('U1', 'ARM', 'N5 restore/planner/H2 generation/output serialization/fullRUN IRQ actual cycles and memory'),
        ('U2', 'FPGA_host', 'Output packet parser/head arbitration/typed packet retirement and CRC service'),
        ('U3', 'FPGA_cross_clock', 'Host parser to NES core transfer and phase-specific captured/display lease binding'),
        ('U4', 'FPGA_SNES', 'Range staging to actual DMA completion/token receipt, bank/display serial history'),
        ('U5', 'FPGA', 'Map staging RAM, descriptor storage, arbitration with existing tile aperture and credit lifetime'),
        ('U6', 'SNES', 'Actual typed setup, ordinary payload copy/DMA, dispatch and polling not covered by retained marks'),
        ('U7', 'whole_path', 'VBlank waits, NES capture/execute overlap, audio/input scheduling, final retire stalls'),
        ('U8', 'FPGA_ARM_SNES', 'tail CRC/fresh scroll/OAM/H2 transport and coverage binding; final check removal approval'),
    ]
    for rel in ['tools/analyze_nes_schedule248.py', 'tools/analyze_nes_joint249.py',
                'tools/analyze_nes_joint250.py', 'tools/analyze_nes_joint251.py',
                'tools/analyze_nes_binding252.py', 'tools/analyze_nes_joint253.py',
                'tools/analyze_nes_joint254.py', 'tools/analyze_nes_joint255.py',
                'analysis/source240-verification.json', 'analysis/runtime233-verification.json']:
        pin(pub(rel))
    result = dict(passed=True, stage=256, scope=__doc__, merged129=MERGED129,
        schedule_rows=len(rows), warm_frames=69, heavy_frames=heavy, components=components,
        max_reconciliation_error_ms=max(abs(r['reconstructed_conditional_ms']-r['prior255_ms']) for r in rows),
        summaries=summaries, old_board_MAP_hierarchy=area,
        candidate_standalone_MAP=joint['area_joint'], wholeboard_savings_proven=False,
        static_observations=observations,
        integration_findings=['255 output lease uses collector ownership;240 export releases collector and waits on separate display lease.',
                              '255 byte acceptance cannot stand in for SNES DMA completion or final display ACK.',
                              '240 sink module is named nes_sink_spi165 but contains four-packet queue184 behavior.'],
        unknown_costs=[dict(id=i, owner=o, required_measurement=t, time_ms=None, area_LE=None) for i,o,t in unknowns],
        new_RTL=False, new_MAP=False, new_FIT=False, new_SNES=False, new_ARM_execution=False,
        R0_scope='boundary and accounting inventory only; no product adoption or timing approval',
        input_hashes=pins)
    def dump(name, value):
        (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    dump('result.json', result)
    for name, table in [('costs.csv', rows), ('area.csv', area)]:
        with (out/name).open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(table[0]), lineterminator='\n')
            w.writeheader(); w.writerows(table)
    shutil.copyfile(__file__, out/'analyzer.py')
    print(json.dumps({k:result[k] for k in ['schedule_rows','warm_frames','max_reconciliation_error_ms','summaries']}, indent=2))


if __name__ == '__main__':
    main()
