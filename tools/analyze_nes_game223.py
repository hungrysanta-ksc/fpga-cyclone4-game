# SPDX-License-Identifier: MIT
"""Reconcile physical223 evidence; comparisons are observational, not controlled FPS."""
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
    f = fields(raw/'nes-game-last-223.txt')
    b = fields(raw/'nes-budget-223.txt')
    assert f['candidate'] == 'NES-GAME-223'
    assert f['board_expected_hex'] == f['board_observed_hex'] == '74'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for k in ['verified', 'end_accepted', 'start_sent', 'run_passed', 'stop_ok',
              'base_restored', 'safe_to_reload', 'spc_unmute_confirmed', 'native_result']:
        assert f[k] == '1', k
    for k in ['verify_error', 'run_error', 'run_rom_error', 'run_first_error',
              'run_stop_error', 'native_sink_error', 'native_video_error',
              'sink_window_error', 'trace_aborts', 'fault_context_valid', 'plan_error']:
        assert f[k] == '0', k
    assert f['native_receiver_error'] == '24'
    assert f['trace_begins'] == '417'
    assert f['trace_ends'] == f['trace_commits'] == f['native_frames'] == '416'
    assert f['trace_generation'] == '598' and f['native_generation'] == '597'
    assert f['sink_window_sent'] == f['sink_window_retired'] == '12242'
    assert f['screen_telemetry_trusted'] == '0'
    assert f['screen_error_field_role'] == 'SPC_INIT_RESULT_165'
    assert b['budget_schema'] == '222' and b['columns'] == ','.join(COLS)
    assert b['values'] == 'HEX32' and b['failed_transfers'] == '0' and b['open'] == '1'
    assert b['startup_reason'] == '6' and b['startup_post_reason'] == '1'
    assert b['startup_signals_hex'] == '00060707'
    assert b['startup_reply_hex'] == '00'*20
    assert b['startup_post_reply_hex'] == '00f7'+'00'*17+'fe'
    assert b['boot_reason'] == '1' and b['boot_polls'] == '428' and b['boot_ticks'] == '4'
    assert b['boot_last_hex'] == '0104a903' and b['plan_valid'] == '0'
    stages = [dict(re.findall(r'(\w+)=(\S+)', x)) for x in
              (raw/'nes-progress-223.txt').read_text().splitlines() if x.strip()]
    assert [int(s['seq']) for s in stages] == list(range(100))
    by = {s['stage']: s for s in stages}
    duration = int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration == 60060 and by['MENU_PREPARED']['elapsed_ms'] == '293760'
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
    assert totals['frames'] == 416 and wire == int(f['native_wire_bytes']) == 7192096
    assert totals['plan'] == int(f['profile_build_stage_ticks']) == 2010
    assert totals['seal'] == int(f['profile_seal_ack_ticks']) == 1997
    assert totals['recv'] == 1968 and int(f['profile_receive_ticks']) == 1968
    assert totals['other'] == totals['frames']*7
    sources = BASE/'probes/nes-ingress223/arm01/src'
    names = ['nes_native_runtime165.c','nes_native_runtime165.h','nes_native165.c',
             'nes_budget210.c','nes_startup222.inc','nes_runtime_board165.inc']
    runtime = (sources/names[0]).read_text()
    receiver = (sources/names[2]).read_text()
    assert 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
    assert 'if(!s->result)s->result=(uint8_t)reason' in runtime
    assert 'frame(tx,0xd2,tok,0);if(!fn(ctx,tx,rx,8)||!status(rx))' in receiver
    assert 'return fail(s,24)' in receiver
    # Two independent tick samples explain the allowed receive accounting skew.
    assert 'nes_trace166.receive_ticks+=s->ticks(s->ctx)-nes_trace166.mark_tick;' in runtime
    assert 'nes_budget210_time(B210_RECEIVE,s->ticks(s->ctx)-nes_trace166.mark_tick);' in runtime
    beforepath = ROOT/'analysis/game222-hardware01-verification.json'
    old = json.loads(beforepath.read_bytes())
    before = old['comparison']['current222']
    count = totals['frames']
    current = dict(duration_ms=duration, display_completed=count,
        display_completed_per_s=count*1000/duration, amortized_display_ms=duration/count,
        receive_ms=int(f['profile_receive_ticks'])*10, receive_bin_ms=totals['recv']*10,
        build_stage_ms=totals['plan']*10, seal_ack_ms=totals['seal']*10,
        planner_inclusive_ms=totals['planner_ticks']*10, callback_ms=totals['callback_ticks']*10,
        planner_minus_callback_ms=(totals['planner_ticks']-totals['callback_ticks'])*10,
        transactions=int(f['native_transactions']), clocked_bytes=wire, window_packets=12242)
    metrics = dict(count_change_percent=(count/before['display_completed']-1)*100,
        d1_bytes_per_completion=totals['d1_payload']/count,
        d1_bytes_per_completion_before=old['totals']['d1_payload']/before['display_completed'],
        d1_encoded_wire_ms_per_completion=totals['d1_payload']*8000/2625000/count,
        ingress_wire_ms_per_completion=totals['ingress']*8000/2625000/count,
        counted_wire_ms_per_completion=wire*8000/2625000/count,
        d0_wire_seconds=totals['d0_clock']*8/2625000,
        max_display_gap_ms=max(r['maxgap'] for r in bins)*10,
        wire_share_percent={k:100*totals[k]/wire for k in WIRE},
        phase_ms_per_completion={k:current[k]/count for k in ['receive_ms','build_stage_ms','seal_ack_ms']})
    metrics['d1_per_completion_reduction_percent']=(1-metrics['d1_bytes_per_completion']/metrics['d1_bytes_per_completion_before'])*100
    result = dict(candidate=223, passed=True, raw_inputs=pins, fields=f, budget_fields=b,
        stages=stages, bins=bins, totals=totals, metrics=metrics,
        comparison=dict(before222=before,current223=current,controlled=False,baseline_sha256=sha(beforepath)),
        terminal=dict(primary='deadline1',secondary='receiver24 D2 callback false OR status invalid',
            last_display_ms=59990,pending_generation=598,partial_frame=True,
            interpretation='Actual transfer guards before/after IO set and preserve primary deadline. Consistent with expected60s termination during nextD2; not independent ACK/status corruption proof. Raw D2 reply not captured.'),
        startup=dict(pre='NO_RESPONSE6/allzero',post='READY1/emptyF7CRC',boot='READY/428polls/40ms',
            deferred_path_observed=True,physical_WR_sampled=False),
        hardware=dict(user_visible_gain=True,user_game_normal=True,user_sound_normal=True,
            user_menu_normal=True,fps60_proven=False,universal_stability_proven=False),
        video=dict(file='IMG_3709.MOV',duration_s=63.63,
            method='127FFmpeg2fps samples;64one-second samples visually reviewed on3contact sheets',
            events_video_seconds=[['0-2','opening'],['3-5','title/player selection'],['6-10','world map'],
                ['11-12','first level transition'],['13-46','first level; scrolling especially16-17,26-43; death/exit near43-46'],
                ['47-50','world map'],['51-52','reentry'],['53-59','first level movement and scrolling'],
                ['60-61','last image held during exit'],['62-63','cartridge menu']],
            exact_host_alignment=False,audio_independently_reviewed=False,
            notes='Scene sampling only, not motion/FPS measurement. User confirms audio. CRT artifacts ignored. End-of-run hold not classified as game freeze.'),
        source_pins={str((sources/n).relative_to(BASE)).replace(chr(92),'/'):sha(sources/n) for n in names},
        findings=['416completed in60.06s versus365in60.09s. Scene/input distributions differ; not controlled FPS gain.',
            'D1 encoded payload2444910B versus2851105B while more displays completed; per-completion reduction24.76%, consistent with geometry packing benefit, not isolated causal proof.',
            'Receive19.68s,build20.10s,seal19.97s: all three remain material. Fewer ingress bytes alone cannot deliver60fps.',
            'Current D1 alone17.91ms/completion and counted sharedSPI52.69ms/completion. Compressible amortized current traffic including terminal partial, not universal NES lower bounds.',
            'Full game/source-read/VBlank counts and exact scene-host synchronization remain unmeasured.'],
        limitations=['10ms phase quantization; planner callback subtraction is not CPU-cycle accounting.',
            'FRAME_START bins are not exact video scene windows; finalbin includes incomplete work.',
            'Wire excludes separate service/audio and parallel aperture DMA. Byte share is not elapsed share.',
            'BG/OBJ are slot extents; mapdirty is previous-display64B blocks, not inactive-bank union upload.',
            'User confirms improvement; sampled video cannot establish actual60Hz presentation.'],
        next='Optimize scroll-aware map work and ingress/plan/seal jointly against16.67ms. First cost current E0/E1 map/command traffic and exact bank-base coverage; reduce redundant map rebuild/upload. Preserve physicalCHR/row-alt/mask/epoch/bank/finalACK and futuremapper semantics. ARM1912B,FPGA159LE/2LAB/9M9K spare; no blind cache growth/saveSRAM use. Minimal boundary tests then first-level scrolling. No unchanged223/044 repeat, startup/FIT/poll-only loop.',
        new_firmware=False,new_fit=False,public_source_sha256=sha(Path(__file__)))
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (a.archive/'analysis.json').write_text(text,encoding='utf8',newline='\n')
    (ROOT/'analysis/game223-hardware01-verification.json').write_text(text,encoding='utf8',newline='\n')
    (a.archive/'progress.json').write_text(json.dumps(dict(status='hardware60s_pass_performance_open',
        next=result['next'],fps60=False,new_firmware=False),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(current=current,metrics=metrics),ensure_ascii=False))

if __name__=='__main__':
    main()
