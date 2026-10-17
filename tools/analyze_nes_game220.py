# SPDX-License-Identifier: MIT
"""Reconcile physical220 logs; video observations remain separate from MCU bins."""
from pathlib import Path
import argparse
import json
import re
from analyze_nes_game213 import ROOT, BASE, sha, fields

WIRE = 'ingress e8 e9 e0 e1 other'.split()
COLS = 'frames recv plan seal maxgap ingress e8 e9 e0 e1 other plans out slot_hits reserved0 reserved1 bg obj mapdirty'.split()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    a = p.parse_args()
    assert not (a.archive / 'manifest01.json').exists(), 'Do not rewrite a sealed archive'
    raw = a.archive / 'raw'
    pins = json.loads((a.archive / 'inputs.json').read_bytes())
    for n, v in pins.items():
        assert sha(raw / n) == v['sha256'] and (raw / n).stat().st_size == v['bytes'], n
    f = fields(raw / 'nes-game-last-220.txt')
    b = fields(raw / 'nes-budget-220.txt')
    assert f['candidate'] == 'NES-GAME-220'
    assert f['board_expected_hex'] == f['board_observed_hex'] == '74'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for k in ['verified', 'end_accepted', 'start_sent', 'run_passed', 'stop_ok',
              'base_restored', 'safe_to_reload', 'spc_unmute_confirmed', 'native_result']:
        assert f[k] == '1', k
    for k in ['verify_error', 'run_error', 'run_rom_error', 'run_first_error',
              'run_stop_error', 'native_receiver_error', 'native_sink_error',
              'native_video_error', 'sink_window_error', 'trace_aborts', 'fault_context_valid']:
        assert f[k] == '0', k
    assert f['plan_error'] == '2' and b['plan_valid'] == '0'
    assert f['trace_begins'] == f['trace_ends'] == f['trace_commits'] == '266'
    assert f['native_frames'] == '265' and f['native_generation'] == '382'
    assert f['trace_generation'] == '383' and f['profile_last_display_tick'] == '5981'
    assert f['sink_window_sent'] == f['sink_window_retired'] == '6797'
    assert f['screen_telemetry_trusted'] == '0' and f['screen_error_field_role'] == 'SPC_INIT_RESULT_165'
    assert b['budget_schema'] == '215' and b['model'] == 'ACTUAL_BANK_RESIDENT_SLOTS_211'
    assert b['columns'] == ','.join(COLS) and b['values'] == 'HEX32'
    assert b['failed_transfers'] == '0' and b['open'] == '1'
    stages = [dict(re.findall(r'(\w+)=(\S+)', s)) for s in
              (raw / 'nes-progress-220.txt').read_text().splitlines() if s.strip()]
    assert [int(s['seq']) for s in stages] == list(range(100))
    by = {s['stage']: s for s in stages}
    duration = int(by['DISPLAY_STOPPED']['elapsed_ms']) - int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration == 60080 and by['MENU_PREPARED']['elapsed_ms'] == '294990'
    bins = []
    for i in range(12):
        values = b[f'b{i:02}'].split(',')
        assert len(values) == len(COLS) and all(len(v) == 8 for v in values)
        r = dict(zip(COLS, (int(v, 16) for v in values)))
        assert r['reserved0'] == r['reserved1'] == 0
        n = r['frames']; wire = sum(r[k] for k in WIRE)
        r.update(frame_start_window_s=[5*i, 5*(i+1)], scene='NOT_EXACTLY_ALIGNED',
                 terminal_partial=i == 11, clocked_bytes=wire,
                 phase_ms_per_completion={k: r[k]*10/n for k in ['recv', 'plan', 'seal']},
                 counted_wire_ms_per_completion=wire*8000/2625000/n,
                 remove_e8_e0_only_wire_ms_per_completion=(wire-r['e8']-r['e0'])*8000/2625000/n,
                 ingress_wire_ms_per_completion=r['ingress']*8000/2625000/n,
                 map_dirty_blocks_per_completion=r['mapdirty']/n,
                 bg_slot_extent_per_completion=r['bg']/n)
        bins.append(r)
    totals = {k: sum(r[k] for r in bins) for k in COLS if k != 'maxgap'}
    totals['maxgap'] = max(r['maxgap'] for r in bins)
    assert totals['frames'] == 265 and sum(totals[k] for k in WIRE) == int(f['native_wire_bytes']) == 4563094
    for k, key in [('recv', 'profile_receive_ticks'), ('plan', 'profile_build_stage_ticks'), ('seal', 'profile_seal_ack_ticks')]:
        assert totals[k] == int(f[key])
    assert totals['other'] == totals['frames']*7
    assert totals['e8'] % 20 == totals['e0'] % 20 == 0
    current = dict(duration_ms=duration, display_completed=265, display_completed_per_s=265000/duration,
                   amortized_display_ms=duration/265, receive_ms=totals['recv']*10,
                   build_stage_ms=totals['plan']*10, seal_ack_ms=totals['seal']*10,
                   transactions=int(f['native_transactions']), clocked_bytes=4563094,
                   window_packets=int(f['sink_window_sent']))
    oldpath = ROOT / 'analysis/game210-hardware01-verification.json'
    before = json.loads(oldpath.read_bytes())['comparison']['current210']
    sources = BASE / 'probes/nes-status220/arm01/src'
    names = ['nes_native_runtime165.c', 'nes_native_runtime165.h', 'nes_budget210.c',
             'nes_plan_service200.c', 'nes_planner211.c', 'nes_resident211.c', 'nes_native_sink165.c']
    runtime = (sources / names[0]).read_text()
    service = (sources / 'nes_plan_service200.c').read_text()
    assert 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
    assert 'if(!p->guard(p->ctx))return fail(p,2)' in service
    assert 'if(!s->result)s->result=(uint8_t)reason' in runtime
    metrics = dict(wire_share_percent={k: 100*totals[k]/4563094 for k in WIRE},
                   pure_counted_wire_seconds=4563094*8/2625000,
                   ingress_wire_ms_per_completion=totals['ingress']*8000/2625000/265,
                   remove_e8_e0_only_wire_ms_per_completion=(4563094-totals['e8']-totals['e0'])*8000/2625000/265,
                   measured_phase_seconds={k: totals[k]/100 for k in ['recv', 'plan', 'seal']},
                   max_display_gap_ms=totals['maxgap']*10)
    result = dict(candidate=220, passed=True, raw_inputs=pins, fields=f, budget_fields=b,
        stages=stages, bins=bins, totals=totals, metrics=metrics,
        comparison=dict(before210=before, current220=current, controlled=False, baseline_sha256=sha(oldpath)),
        terminal=dict(primary='deadline1', secondary='plan2 guard cancellation, no recorded215 status fault',
                      last_display_ms=59810, pending_generation=383, partial_frame=True,
                      interpretation='Consistent with intended60s deadline, not repeated215 FPGA fault. Last ACK0 and untrusted screen_frames0 do not invalidate265 displays.'),
        hardware=dict(user_60s_play=True, user_menu_sound_input_normal=True, user_opening_improved=True,
                      user_scroll_still_stutters=True, observed_early_termination_resolved=True,
                      universal_stability_proven=False, fps60_proven=False),
        video=dict(file='IMG_3706.MOV', duration_s=62.03, method='124 FFmpeg2fps samples extracted;62 samples on two1fps contact sheets visually reviewed',
                   events_video_seconds=[['0-1', 'opening'], ['2-4', 'player selection'], ['5-11', 'world map'],
                       ['12-13', 'level transition'], ['14-19', 'first level, movement then death'],
                       ['20-23', 'world map'], ['24-25', 'transition'], ['26-34', 'first level; clear scrolling around28-30'],
                       ['35-37', 'world map'], ['38-39', 'transition'], ['40-46', 'first level; clear scrolling around42-43'],
                       ['47-50', 'world map'], ['51', 'transition'], ['52-60', 'first level; scrolling around54-55'],
                       ['61', 'cartridge menu visible']],
                   exact_host_alignment=False, notes='Recording starts with game already visible. MENU_PREPARED is not a filmed timestamp; shutdown holds last image. Do not assign exact MCU bins or derive FPS from2fps samples. Audio confirmed by user; not independently measured. CRT diagonal/color bands excluded.'),
        source_pins={p.relative_to(BASE).as_posix():sha(p) for p in [sources/n for n in names]},
        findings=['Actual persistent-slot reuse is active:22984 retained-destination hits;1938 emitted plans/38320 outputB include zero anchors and in-flight work.',
                  'Plan phase34.68s is dominant but includes CPU conversion/search, callbacks, source/chunk waits and service. Not CPU-only.',
                  'Planner still reconstructs every geometry cell; same-frame exact-key and retained-slot searches are linear. Larger slot extent is a scaling candidate, not a measured cause.',
                  'D0-D3 ingress alone averages26.04ms counted SPI per completion, above16.67ms; includes polls/control and terminal partial work, not irreducible payload.',
                  'mapdirty counts64B changes from last display, not actual inactive-bank union uploads. E1 is mixed commands; neither proves map-only bottleneck.'],
        limitations=['Frame-start bins can cross5s boundaries; b11 includes incomplete terminal frame.',
                     'No exact actual source-miss/SNES VBlank/CPU subphase counters or captured full scroll geometries.',
                     'SPI bytes exclude separate service/audio and parallel aperture DMA. Byte shares are not elapsed-time shares.',
                     'slot_hits counts retained destination reuse, not every same-frame dedupe; bg/obj are slot extents, not count of changed tiles.',
                     'Comparison210 differs in scenes and inputs; no controlled gain/FPS/root-cause exclusivity claim.'],
        next='Prioritize joint ingress/control reduction + incremental/indexed geometry planning + scroll-aware map. Reuse current215/216 failure evidence; no further loader/FIT/cache-only loop. With next performance implementation, minimally split CPU planning vs callback/drain and useful ingress vs polls; preserve exact physical keys/row-alt/mask/epoch/bank/finalACK and fullARM/IRQ margin checks. Budget ARM4952 spare and FPGA252LE/6LAB/9M9K; no saveSRAM. Then actual SMB3 first-level scrolling; no unchanged220/044 repeat.',
        new_firmware=False, new_fit=False, public_source_sha256=sha(Path(__file__)))
    text = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    (a.archive/'analysis.json').write_text(text, encoding='utf8', newline='\n')
    (ROOT/'analysis/game220-hardware01-verification.json').write_text(text, encoding='utf8', newline='\n')
    (a.archive/'progress.json').write_text(json.dumps(dict(status='hardware60s_pass_performance_open',
         next=result['next'], fps60=False, new_firmware=False), ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(current=current, metrics=metrics, totals=totals), ensure_ascii=False))


if __name__ == '__main__':
    main()
