# SPDX-License-Identifier: MIT
"""Reconcile physical222 evidence; comparisons are observational, not controlled FPS."""
from pathlib import Path
import argparse
import json
import re
from analyze_nes_game213 import ROOT, BASE, sha, fields

WIRE = 'ingress e8 e9 e0 e1 other'.split()
COLS = ('frames recv plan seal maxgap ingress e8 e9 e0 e1 other plans out '
        'slot_hits planner_ticks callback_ticks bg obj mapdirty d1_payload d0_clock').split()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    a = parser.parse_args()
    assert not (a.archive / 'manifest01.json').exists(), 'Sealed archive is immutable'
    raw = a.archive / 'raw'
    pins = json.loads((a.archive / 'inputs.json').read_bytes())
    for name, pin in pins.items():
        assert sha(raw/name) == pin['sha256']
        assert (raw/name).stat().st_size == pin['bytes']
    f = fields(raw/'nes-game-last-222.txt')
    b = fields(raw/'nes-budget-222.txt')
    assert f['candidate'] == 'NES-GAME-222'
    assert f['board_expected_hex'] == f['board_observed_hex'] == '74'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for k in ['verified', 'end_accepted', 'start_sent', 'run_passed', 'stop_ok',
              'base_restored', 'safe_to_reload', 'spc_unmute_confirmed', 'native_result']:
        assert f[k] == '1', k
    for k in ['verify_error', 'run_error', 'run_rom_error', 'run_first_error',
              'run_stop_error', 'native_sink_error', 'native_video_error',
              'sink_window_error', 'trace_aborts', 'fault_context_valid', 'plan_error']:
        assert f[k] == '0', k
    assert f['native_receiver_error'] == '23'
    assert f['trace_begins'] == '366'
    assert f['trace_ends'] == f['trace_commits'] == f['native_frames'] == '365'
    assert f['trace_generation'] == '576' and f['native_generation'] == '575'
    assert f['sink_window_sent'] == f['sink_window_retired'] == '11082'
    assert f['screen_telemetry_trusted'] == '0'
    assert f['screen_error_field_role'] == 'SPC_INIT_RESULT_165'
    assert b['budget_schema'] == '222' and b['columns'] == ','.join(COLS)
    assert b['values'] == 'HEX32' and b['failed_transfers'] == '0' and b['open'] == '1'
    assert b['startup_reason'] == '6' and b['startup_post_reason'] == '1'
    assert b['startup_signals_hex'] == '00060707'
    assert b['startup_reply_hex'] == '00'*20
    assert b['startup_post_reply_hex'] == '00f7'+'00'*17+'fe'
    assert b['boot_reason'] == '1' and b['boot_polls'] == '431' and b['boot_ticks'] == '5'
    assert b['boot_last_hex'] == '0104a903' and b['plan_valid'] == '0'
    stages = [dict(re.findall(r'(\w+)=(\S+)', x)) for x in
              (raw/'nes-progress-222.txt').read_text().splitlines() if x.strip()]
    assert [int(s['seq']) for s in stages] == list(range(100))
    by = {s['stage']: s for s in stages}
    duration = int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration == 60090 and by['MENU_PREPARED']['elapsed_ms'] == '298200'
    bins = []
    for i in range(12):
        values = b[f'b{i:02}'].split(',')
        assert len(values) == len(COLS) and all(len(v) == 8 for v in values)
        r = dict(zip(COLS, (int(v, 16) for v in values)))
        wire = sum(r[k] for k in WIRE)
        r.update(frame_start_window_s=[5*i, 5*(i+1)], terminal_partial=i == 11,
                 scene='NO_EXACT_HOST_VIDEO_ALIGNMENT', clocked_bytes=wire,
                 d1_encoded_wire_ms_per_completion=r['d1_payload']*8000/2625000/r['frames'],
                 counted_wire_ms_per_completion=wire*8000/2625000/r['frames'],
                 phase_ms_per_completion={k:r[k]*10/r['frames'] for k in ['recv','plan','seal']})
        bins.append(r)
    totals = {k:sum(r[k] for r in bins) for k in COLS if k != 'maxgap'}
    totals['maxgap'] = max(r['maxgap'] for r in bins)
    wire = sum(totals[k] for k in WIRE)
    assert totals['frames'] == 365 and wire == int(f['native_wire_bytes']) == 7481069
    assert totals['plan'] == int(f['profile_build_stage_ticks']) == 1941
    assert totals['seal'] == int(f['profile_seal_ack_ticks']) == 1839
    assert totals['recv'] == 2193 and int(f['profile_receive_ticks']) == 2189
    assert totals['other'] == totals['frames']*7
    sources = BASE/'probes/nes-startup222/arm02/src'
    names = ['nes_native_runtime165.c','nes_native_runtime165.h','nes_native165.c',
             'nes_budget210.c','nes_startup222.inc','nes_runtime_board165.inc']
    runtime = (sources/names[0]).read_text()
    receiver = (sources/names[2]).read_text()
    assert 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
    assert 'if(!s->result)s->result=(uint8_t)reason' in runtime
    assert 'if(!fn(ctx,tx,rx,n+3)||crc16(rx+1,n)' in receiver
    assert 'return fail(s,23)' in receiver
    # Two independent tick samples explain the allowed receive accounting skew.
    assert 'nes_trace166.receive_ticks+=s->ticks(s->ctx)-nes_trace166.mark_tick;' in runtime
    assert 'nes_budget210_time(B210_RECEIVE,s->ticks(s->ctx)-nes_trace166.mark_tick);' in runtime
    beforepath = ROOT/'analysis/game220-hardware01-verification.json'
    before = json.loads(beforepath.read_bytes())['comparison']['current220']
    current = dict(duration_ms=duration, display_completed=365,
                   display_completed_per_s=365000/duration, amortized_display_ms=duration/365,
                   receive_ms=21890, receive_bin_ms=21930, build_stage_ms=19410,
                   seal_ack_ms=18390, planner_inclusive_ms=11990, callback_ms=580,
                   planner_minus_callback_ms=11410, transactions=int(f['native_transactions']),
                   clocked_bytes=wire, window_packets=11082)
    metrics = dict(wire_share_percent={k:100*totals[k]/wire for k in WIRE},
                   pure_counted_wire_seconds=wire*8/2625000,
                   d1_encoded_wire_ms_per_completion=totals['d1_payload']*8000/2625000/365,
                   ingress_wire_ms_per_completion=totals['ingress']*8000/2625000/365,
                   d0_wire_seconds=totals['d0_clock']*8/2625000,
                   max_display_gap_ms=totals['maxgap']*10,
                   measured_phase_seconds=dict(receive=21.89, plan=19.41, seal=18.39),
                   receive_counter_skew_ms=40,
                   count_change_percent=(365/265-1)*100,
                   build_phase_ms_per_completion_before=before['build_stage_ms']/265,
                   build_phase_ms_per_completion_current=19410/365)
    result = dict(candidate=222, passed=True, raw_inputs=pins, fields=f, budget_fields=b,
        stages=stages, bins=bins, totals=totals, metrics=metrics,
        comparison=dict(before220=before, current222=current, controlled=False, baseline_sha256=sha(beforepath)),
        terminal=dict(primary='deadline1', secondary='receiver23 transfer callback OR CRC condition; not independent CRC proof',
                      last_display_ms=59970, pending_generation=576, partial_frame=True,
                      interpretation='Guard records deadline first and preserves it; next D1 may return false at the deadline. Consistent with intended60s exit, not new independent transfer/ROM/display fault.'),
        startup=dict(pre='NO_RESPONSE6/allzero', post='READY1/emptyF7CRC', boot='READY/431polls/50ms',
                     deferred_path_observed=True, physical_WR_sampled=False,
                     physical_root221_proven=False, note='Stack lifetime and pre/post handshake both changed; no causal A/B. Signal samples are RESET/DONE/RDY, not waveforms.'),
        hardware=dict(user_visible_gain=True, user_extended_firstlevel_scroll=True,
                      user_normal_play_still_insufficient=True, menu_visible=True,
                      universal_stability_proven=False, fps60_proven=False),
        video=dict(file='IMG_3708.MOV', duration_s=66.63,
                   method='133FFmpeg2fps samples;67one-second samples on3contact sheets visually reviewed',
                   events_video_seconds=[['0-1','loading/menu'],['2-5','opening'],['6-7','player selection'],
                       ['8-13','world map'],['14','level transition'],['15-45','first level, movement/death at end'],
                       ['18-24,29-40','clear background scrolling within first level'],['46-49','world map'],
                       ['50-51','level transition'],['52-61','first level and further scrolling'],
                       ['62-64','last image held during exit'],['65-66','cartridge menu']],
                   exact_host_alignment=False, audio_independently_reviewed=False,
                   notes='Samples identify scenes, not FPS. User reports improvement. CRT bands/color ignored. STOP/menu recovery holds last image; do not count held exit image as game freeze.'),
        source_pins={str((sources/n).relative_to(BASE)).replace('\\','/'):sha(sources/n) for n in names},
        findings=['365 completed displays vs220265; scene/input distribution differs, not controlled37.7%FPS gain.',
                  'Plan phase19.41s vs34.68s supports useful planner improvement; causal effect not isolated.',
                  'Planner11.99s includes0.58s emit callbacks; approximate non-callback11.41s still not CPU-cycle accounting.',
                  'D1 encoded payload2851105B alone averages23.81ms per completion at2.625MHz. Includes record headers and terminal partial; compressible, not universal NES bandwidth lower bound.',
                  'D0 polls396496B only about1.21s wire/session: poll-only change cannot meet16.67ms.',
                  'Receive21.89s/build19.41s/seal18.39s are now all material. Geometry ingress, processing and scroll-map traffic must be budgeted jointly.'],
        limitations=['Budget receive21.93s vsprofile21.89s comes from separately sampled10ms ticks; retain both raw values.',
                     'Frame-start bins are not exact video scene windows; terminal b11 includes unfinished work.',
                     'Wire counts exclude separate service/audio and parallel aperture DMA; byte shares are not elapsed shares.',
                     'BG/OBJ are slot extents, not dirty tiles; mapdirty is previous-display64B blocks, not inactive-bank union upload count.',
                     'Source reads/SNESVBlank and actual full scroll geometry are unmeasured; no inferred physical waveform/root cause.'],
        next='Return to performance: compact/incremental geometry ingress and scroll-aware map with actual scrolling cost model, shared16.67ms budget. Prioritize reducing repeated encoded geometry before poll-only changes; preserve row/alt/mask/physicalCHR identity/epoch/base-bank/finalACK. ARM1912B headroom precludes blind cache growth; preserve saveSRAM/GBC164 and future mapper semantics. Minimal boundary checks then real first-level scrolling, no unchanged222/044 repeat or startup/FIT loop.',
        new_firmware=False, new_fit=False, public_source_sha256=sha(Path(__file__)))
    text = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    (a.archive/'analysis.json').write_text(text,encoding='utf8',newline='\n')
    (ROOT/'analysis/game222-hardware01-verification.json').write_text(text,encoding='utf8',newline='\n')
    (a.archive/'progress.json').write_text(json.dumps(dict(status='hardware60s_pass_performance_open',
        next=result['next'], fps60=False, new_firmware=False),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(current=current, metrics=metrics, totals=totals),ensure_ascii=False))


if __name__ == '__main__':
    main()
