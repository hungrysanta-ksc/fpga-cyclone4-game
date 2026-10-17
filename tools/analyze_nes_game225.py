# SPDX-License-Identifier: MIT
"""Reconcile physical225 with223; different scenes are not a controlled FPS test."""
from pathlib import Path
import argparse
import json
import re
from analyze_nes_game213 import ROOT, BASE, sha, fields
from analyze_nes_game223 import COLS, WIRE


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    a = p.parse_args().archive
    assert not (a/'manifest01.json').exists(), 'Sealed evidence is immutable'
    pins = json.loads((a/'inputs.json').read_bytes())
    for name, pin in pins.items():
        assert sha(a/'raw'/name) == pin['sha256']
        assert (a/'raw'/name).stat().st_size == pin['bytes']
    f = fields(a/'raw/nes-game-last-225.txt')
    b = fields(a/'raw/nes-budget-225.txt')
    assert f['candidate'] == 'NES-GAME-225'
    assert f['board_expected_hex'] == f['board_observed_hex'] == '74'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for k in ['verified', 'end_accepted', 'start_sent', 'run_passed', 'stop_ok',
              'base_restored', 'safe_to_reload', 'spc_unmute_confirmed', 'native_result']:
        assert f[k] == '1', k
    for k in ['load_result', 'file_result', 'verify_error', 'run_error', 'run_rom_error',
              'run_first_error', 'run_stop_error', 'native_sink_error', 'native_video_error',
              'sink_window_error', 'trace_aborts', 'fault_context_valid', 'plan_error']:
        assert f[k] == '0', k
    assert f['native_receiver_error'] == '24'
    assert f['trace_begins'] == '402'
    assert f['trace_ends'] == f['trace_commits'] == f['native_frames'] == '401'
    assert f['native_generation'] == '668' and f['trace_generation'] == '669'
    assert f['sink_window_sent'] == f['sink_window_retired'] == '11320'
    assert f['screen_telemetry_trusted'] == '0'
    assert f['screen_error_field_role'] == 'SPC_INIT_RESULT_165'
    assert f['spc_init_status_hex'] == 'a9' and f['screen_error'] == '169'
    assert b['columns'] == ','.join(COLS) and b['values'] == 'HEX32'
    assert b['budget_schema'] == '222' and b['bin_basis'] == 'FRAME_START_NOT_SCENE'
    assert b['failed_transfers'] == '0' and b['open'] == '1'
    assert b['source_reads_snes_vblank'] == 'UNMEASURED'
    assert b['startup_reason'] == '6' and b['startup_post_reason'] == '1'
    assert b['startup_reply_hex'] == '00'*20
    assert b['startup_post_reply_hex'] == '00f7'+'00'*17+'fe'
    assert b['boot_reason'] == '1' and b['boot_polls'] == '428' and b['boot_ticks'] == '5'
    assert b['boot_last_hex'] == '0104a903' and b['plan_valid'] == '0'
    stages = [dict(re.findall(r'(\w+)=(\S+)', line)) for line in
              (a/'raw/nes-progress-225.txt').read_text().splitlines() if line.strip()]
    assert [int(s['seq']) for s in stages] == list(range(100))
    by = {s['stage']: s for s in stages}
    duration = int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration == 60070 and by['MENU_PREPARED']['elapsed_ms'] == '294390'
    bins = []
    for i in range(12):
        values = b[f'b{i:02}'].split(',')
        assert len(values) == len(COLS) and all(len(v) == 8 for v in values)
        r = dict(zip(COLS, (int(v, 16) for v in values)))
        r.update(frame_start_window_s=[5*i, 5*(i+1)], terminal_partial=i == 11,
                 scene='NO_EXACT_HOST_VIDEO_ALIGNMENT')
        bins.append(r)
    totals = {k:sum(r[k] for r in bins) for k in COLS if k != 'maxgap'}
    totals['maxgap'] = max(r['maxgap'] for r in bins)
    wire = sum(totals[k] for k in WIRE)
    assert totals['frames'] == 401 and wire == int(f['native_wire_bytes']) == 7132549
    assert totals['plan'] == int(f['profile_build_stage_ticks']) == 2146
    assert totals['seal'] == int(f['profile_seal_ack_ticks']) == 1829
    assert totals['recv'] == 1969 and int(f['profile_receive_ticks']) == 1968
    assert totals['other'] == totals['frames']*7 and totals['e8'] % 20 == 0
    src = BASE/'probes/nes-scroll225/arm01/src'
    names = ['nes_native_runtime165.c', 'nes_native_runtime165.h', 'nes_native165.c',
             'nes_budget210.c', 'nes_plan_service200.c', 'nes_planner211.c',
             'nes_native_sink165.c', 'nes_resident211.c']
    runtime = (src/names[0]).read_text()
    receiver = (src/names[2]).read_text()
    assert 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
    assert 'if(!s->result)s->result=(uint8_t)reason' in runtime
    assert 'frame(tx,0xd2,tok,0);if(!fn(ctx,tx,rx,8)||!status(rx))' in receiver
    assert 'return fail(s,24)' in receiver
    assert 'nes_trace166.receive_ticks+=s->ticks(s->ctx)-nes_trace166.mark_tick;' in runtime
    assert 'nes_budget210_time(B210_RECEIVE,s->ticks(s->ctx)-nes_trace166.mark_tick);' in runtime
    before_path = ROOT/'analysis/game223-hardware01-verification.json'
    old = json.loads(before_path.read_bytes())
    before = old['comparison']['current223']
    current = dict(duration_ms=duration, display_completed=401,
        display_completed_per_s=401000/duration, amortized_display_ms=duration/401,
        receive_ms=19680, receive_bin_ms=19690, build_stage_ms=21460, seal_ack_ms=18290,
        planner_inclusive_ms=totals['planner_ticks']*10, callback_ms=totals['callback_ticks']*10,
        planner_minus_callback_ms=(totals['planner_ticks']-totals['callback_ticks'])*10,
        build_outside_planner_ms=(totals['plan']-totals['planner_ticks'])*10,
        transactions=int(f['native_transactions']), clocked_bytes=wire, window_packets=11320)
    per = {k:dict(before223=old['totals'][k]/416,current225=totals[k]/401,
                  change_percent=(totals[k]/401/(old['totals'][k]/416)-1)*100)
           for k in COLS if k not in ['frames','maxgap']}
    metrics = dict(per_completion=per, count_change_percent=(401/416-1)*100,
        d1_encoded_wire_ms_per_completion=totals['d1_payload']*8000/2625000/401,
        counted_wire_ms_per_completion=wire*8000/2625000/401,
        max_display_gap_ms=totals['maxgap']*10, e8_status_queries=totals['e8']//20,
        before_e8_status_queries=old['totals']['e8']//20,
        before_build_outside_planner_ms=before['build_stage_ms']-before['planner_inclusive_ms'])
    result = dict(candidate=225, evidence_checks_passed=True, raw_inputs=pins,
        fields=f, budget_fields=b, stages=stages, bins=bins, totals=totals, metrics=metrics,
        comparison=dict(before223=before,current225=current,controlled=False,baseline_sha256=sha(before_path)),
        terminal=dict(primary='deadline1',secondary='receiver24 D2 callback false OR status invalid',
            last_display_ms=int(f['profile_last_display_tick'])*10,pending_generation=669,
            interpretation='Consistent with deadline while next D2 is attempted; no independent ACK corruption proof. Raw D2 reply absent.'),
        hardware=dict(user_static_gain=True,user_scroll_regression_suspected=True,
            user_sound_normal=True,user_menu_normal=True,fps60_proven=False,
            scroll_performance_acceptance=False),
        video=dict(file='IMG_3710.MOV',duration_s=64.30,
            method='129 FFmpeg2fps samples;65one-second samples visually reviewed on4contact sheets',
            events_video_seconds=[['0-3','opening'],['4-5','title/player selection'],['6-11','world map'],
                ['12','first level transition'],['13-18','first level then death'],['19-21','world map'],
                ['22-23','level reentry'],['24-55','first level, background scrolling especially26-36 and40-51'],
                ['56','death/exit'],['57-62','world map including end-of-run hold'],['63-64','cartridge menu']],
            exact_host_alignment=False,audio_reviewed=False,audio_ignored_at_user_request=True,
            notes='Scene samples, not a display FPS measurement. CRT/camera bands and colors ignored.'),
        source_pins={str((src/n).relative_to(BASE)).replace(chr(92),'/'):sha(src/n) for n in names},
        findings=['60.07s/401completions versus60.06s/416. Different routes/deaths; not controlled regression percentage.',
            'Per completion mapdirty-17.82% and E1-8.42%, but E8+43.90%, plans+19.06%, tile output+26.40%. Observed cost shift, not a same-scene cause proof.',
            'Planner inclusive13.54->12.80s; whole build20.10->21.46s. Outside planner6.56->8.66s includes BEGIN/finish/flush/bulk-drain/service, not pure FPGA time.',
            'D1 still17.76ms and countedSPI54.21ms/completion. Current traffic needs structural reduction; not an immutable NES bandwidth lower bound.',
            'Synthetic49.44% map-wire saving did not establish physical scrolling improvement. Physical map-only bytes, source misses, VBlank and exact scene alignment absent.'],
        limitations=['10ms timers; receive bin1969 versus profile1968 arises from separately sampled tick calls.',
            'E8 covers credit/descriptor/END/retire polling. Counts are not actual memory misses or waiting duration.',
            'Mapdirty counts previous-display64Bblocks, not inactive-bank union bytes. E1 includes non-map metadata.',
            'Slot hits/plan count are requests; not a source-cache hit rate. BG/OBJ are slot extents.',
            'Wire excludes separate service/audio and parallel aperture DMA; finalbin includes partial work.'],
        next='Prioritize actual scrolling BEGIN/finish/bulk drain and new physical-tile work together with ingress/fullplanner and64Bmap overhead. Use same captured scrolling geometry/state for223/225 comparison if available; current logs cannot reconstruct it. Add only bounded missing phase/plan-kind/dirty-union data with the next performance change if needed, not a diagnostic-only/FIT loop. Preserve source epoch/row-alt/mask/bank/finalACK and saveSRAM/GBC164. No same225/044 retest. Synthetic map-only or static gain is not acceptance; first-level scrolling and total16.67ms budget are.',
        new_firmware=False,new_fit=False,public_source_sha256=sha(Path(__file__)))
    text = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (a/'analysis.json').write_text(text,encoding='utf8',newline='\n')
    (ROOT/'analysis/game225-hardware01-verification.json').write_text(text,encoding='utf8',newline='\n')
    (a/'progress.json').write_text(json.dumps(dict(status='hardware60s_pass_scroll_performance_not_accepted',
        next=result['next'],fps60=False,new_firmware=False),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(current=current,metrics=metrics),ensure_ascii=False))


if __name__ == '__main__':
    main()
