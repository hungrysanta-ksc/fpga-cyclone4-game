# SPDX-License-Identifier: MIT
"""Reconcile physical226; compare225 without claiming controlled scrolling FPS."""
from pathlib import Path
import argparse
import json
import re
import struct
from analyze_nes_game213 import ROOT, BASE, sha, fields
from analyze_nes_game223 import COLS as OLD_COLS, WIRE

COLS = OLD_COLS + ['begin_ticks', 'finish_ticks']


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    a = p.parse_args().archive
    assert not (a/'manifest01.json').exists(), 'Sealed evidence is immutable'
    pins = json.loads((a/'inputs.json').read_bytes())
    for name, pin in pins.items():
        assert sha(a/'raw'/name) == pin['sha256']
        assert (a/'raw'/name).stat().st_size == pin['bytes']
    f = fields(a/'raw/nes-game-last-226.txt')
    b = fields(a/'raw/nes-budget-226.txt')
    assert f['candidate'] == 'NES-GAME-226'
    assert f['board_expected_hex'] == f['board_observed_hex'] == '74'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for k in ['verified','end_accepted','start_sent','run_passed','stop_ok',
              'base_restored','safe_to_reload','spc_unmute_confirmed','native_result']:
        assert f[k] == '1', k
    for k in ['load_result','file_result','verify_error','run_error','run_rom_error',
              'run_first_error','run_stop_error','native_receiver_error','native_video_error',
              'trace_aborts','fault_context_valid','plan_error']:
        assert f[k] == '0', k
    assert f['native_sink_error'] == f['sink_window_error'] == '2'
    assert f['trace_begins'] == f['trace_ends'] == f['trace_commits'] == '453'
    assert f['native_frames'] == '452'
    assert f['native_generation'] == '745' and f['trace_generation'] == '747'
    assert f['sink_window_sent'] == '13035' and f['sink_window_retired'] == '13034'
    assert f['sink_trace_ack_valid'] == '0' and f['sink_trace_ack_hex'] == '00'*12
    assert f['screen_telemetry_trusted'] == '0'
    assert f['screen_error_field_role'] == 'SPC_INIT_RESULT_165'
    assert f['spc_init_status_hex'] == 'a9' and f['screen_error'] == '169'
    assert b['columns'] == ','.join(COLS) and b['values'] == 'HEX32'
    assert b['budget_schema'] == '226' and b['bin_basis'] == 'FRAME_START_NOT_SCENE'
    assert b['failed_transfers'] == '0' and b['open'] == '1'
    assert b['source_reads_snes_vblank'] == 'UNMEASURED'
    assert b['startup_reason'] == '6' and b['startup_post_reason'] == '1'
    assert b['startup_reply_hex'] == '00'*20
    assert b['startup_post_reply_hex'] == '00f7'+'00'*17+'fe'
    assert b['boot_reason'] == '1' and b['boot_polls'] == '430' and b['boot_ticks'] == '5'
    assert b['boot_last_hex'] == '0104a903' and b['plan_valid'] == '0'
    stages = [dict(re.findall(r'(\w+)=(\S+)', line)) for line in
              (a/'raw/nes-progress-226.txt').read_text().splitlines() if line.strip()]
    assert [int(s['seq']) for s in stages] == list(range(100))
    by = {s['stage']:s for s in stages}
    duration = int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration == 60060 and by['MENU_PREPARED']['elapsed_ms'] == '294490'
    bins = []
    for i in range(12):
        values = b[f'b{i:02}'].split(',')
        assert len(values) == len(COLS) and all(len(v) == 8 for v in values)
        r = dict(zip(COLS,(int(v,16) for v in values)))
        assert r['begin_ticks']+r['planner_ticks']+r['finish_ticks'] == r['plan']
        r.update(frame_start_window_s=[5*i,5*(i+1)],terminal_partial=i==11,
                 scene='NO_EXACT_HOST_VIDEO_ALIGNMENT')
        bins.append(r)
    totals = {k:sum(r[k] for r in bins) for k in COLS if k!='maxgap'}
    totals['maxgap'] = max(r['maxgap'] for r in bins)
    wire = sum(totals[k] for k in WIRE)
    assert totals['frames'] == 452 and wire == int(f['native_wire_bytes']) == 7959019
    assert totals['plan'] == int(f['profile_build_stage_ticks']) == 1600
    assert totals['seal'] == int(f['profile_seal_ack_ticks']) == 2111
    assert totals['recv'] == 2241 and int(f['profile_receive_ticks']) == 2240
    assert totals['planner_ticks'] == 717 and totals['callback_ticks'] == 64
    assert totals['begin_ticks'] == 88 and totals['finish_ticks'] == 795
    assert totals['other'] == totals['frames']*7 and totals['e8']%20 == 0
    src = BASE/'probes/nes-fast226/arm01/src'
    names = ['nes_native_runtime165.c','nes_native_runtime165.h','nes_sink_window184.c',
             'nes_budget210.c','nes_plan_service200.c','nes_planner211.c',
             'nes_native_sink165.c','nes_resident211.c']
    runtime = (src/names[0]).read_text()
    window = (src/names[2]).read_text()
    assert 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
    assert 'if(!s->result)s->result=(uint8_t)reason' in runtime
    assert 'if(!s->guard(s->ctx))return fail(s,2);' in window
    assert 'if(!s->transfer(s->ctx,tx,rx,n))return fail(s,3);' in window
    assert 'return send(s,p,n)&&nes_window184_drain(s,ack);' in window
    assert 'nes_budget210_time(B226_BEGIN' in runtime and 'nes_budget210_time(B226_FINISH' in runtime
    req = struct.unpack('<BBHIHHHH',bytes.fromhex(f['sink_trace_request_hex']))
    assert req == (3,0,35,453,747,0,168,0), req
    before_path = ROOT/'analysis/game225-hardware01-verification.json'
    old = json.loads(before_path.read_bytes())
    before = old['comparison']['current225']
    current = dict(duration_ms=duration,display_completed=452,
        display_completed_per_s=452000/duration,amortized_display_ms=duration/452,
        receive_ms=22400,receive_bin_ms=22410,build_stage_ms=16000,seal_ack_ms=21110,
        planner_inclusive_ms=7170,callback_ms=640,planner_minus_callback_ms=6530,
        build_outside_planner_ms=8830,begin_ms=880,finish_ms=7950,
        transactions=int(f['native_transactions']),clocked_bytes=wire,window_packets=13035)
    per = {k:dict(before225=old['totals'][k]/401,current226=totals[k]/452,
                  change_percent=(totals[k]/452/(old['totals'][k]/401)-1)*100)
           for k in OLD_COLS if k not in ['frames','maxgap']}
    metrics = dict(per_completion=per,count_change_percent=(452/401-1)*100,
        d1_encoded_wire_ms_per_completion=totals['d1_payload']*8000/2625000/452,
        counted_wire_ms_per_completion=wire*8000/2625000/452,
        max_display_gap_ms=totals['maxgap']*10,e8_status_queries=totals['e8']//20)
    next_work = ('Prioritize receive/ingress plus SNES metadata/SEAL and finish/source-drain jointly. '
        'BEGIN0.88s is not the main target; more planner-only or polling/FIT loops cannot establish60fps. '
        'Choose a bounded performance change using current evidence and matched scrolling fixtures; '
        'preserve source epoch, row-alt/mask, both-bank validity, real finalACK, audio/input and commonSTOP. '
        'Measure first-level scroll against total16.67ms. No same226/044 repeat; preserve ARM1792B/saveSRAM/GBC164.')
    result = dict(candidate=226,evidence_checks_passed=True,raw_inputs=pins,
        fields=f,budget_fields=b,stages=stages,bins=bins,totals=totals,metrics=metrics,
        comparison=dict(before225=before,current226=current,controlled=False,baseline_sha256=sha(before_path)),
        terminal=dict(primary='deadline1',secondary='window2 guard denied before next IO',
            last_display_ms=59850,pending_generation=747,
            pending_request=dict(op='SEAL3',sequence=35,serial=453,generation=747,payload_bytes=168),
            packets_sent=13035,packets_retired=13034,displayed_generation=745,ack_valid=False,
            interpretation='Final SEAL drain interrupted by deadline; invalid zero ACK is not a received corrupt ACK. One packet remains unretired at snapshot; generation747 display after snapshot is unproven.'),
        hardware=dict(user_scroll_gain=True,user_sound_normal=True,user_menu_normal=True,
            user_input_explicitly_reported=False,fps60_proven=False,scroll_performance_acceptance=False),
        video=dict(file='IMG_3711.MOV',duration_s=63.97,
            method='128 FFmpeg2fps samples;64one-second samples visually reviewed on4contact sheets',
            events_video_seconds=[['0-2','opening'],['3-4','title/player selection'],['5-9','world map'],
                ['10-11','first level transition'],['12-42','first level; clear scrolling14-17,21-29,34-39'],
                ['43','death/exit'],['44-46','world map'],['47-48','reentry'],
                ['49-60','first level; scrolling53-57'],['61-62','last-frame hold during exit'],['63','cartridge menu']],
            exact_host_alignment=False,audio_reviewed=False,
            notes='Scene samples only, not unique displayFPS. Audio normal per user; CRT/camera bands/colors ignored.'),
        source_pins={str((src/n).relative_to(BASE)).replace(chr(92),'/'):sha(src/n) for n in names},
        findings=['60.06s/452display completions;225 had60.07s/401. User reports scrolling gain. Different scenes/inputs, not controlledFPS percentage.',
            'Planner inclusive12.80->7.17s, percompletion31.92->15.86ms; wholebuild21.46->16.00s. Consistent with planner cost reduction, not CPUcycle or same-scene causal proof.',
            'BEGIN0.88s/planner7.17s/finish7.95s exactly sum16.00s in every bin. Finish includes END/source generation/bulk service/drain, not pure FPGA compute.',
            'Receive22.40s and SEAL21.11s remain dominant; percompletion roughly unchanged. D1 payload and countedSPI alone exceed16.67ms percompletion on current serial path.',
            '453geometryCOMMIT versus452displayACK is terminal partial work, not an extra proved visible frame. Deadline preserves first failure; no CRC/ACK mismatch established.'],
        limitations=['10ms timers; receive bin2241 vs profile2240 uses separately sampled calls.',
            '453successful builds include pendingSEAL; amortized per452displays is aggregate, not per-frame latency distribution.',
            'SEAL timer records successful phases; interrupted finalSEAL time is not fully included. Phase totals are not an exhaustive wall-time partition.',
            'E8 counts credit/descriptor/END/retire queries, not memory misses or pure waiting time.',
            'Mapdirty is previous-display64Bblocks, not inactive-bank union bytes; E1 includes non-map data.',
            'Wire excludes separate audio/service and parallel aperture DMA. 5s bins follow frame start, not video scenes.'],
        next=next_work,new_firmware=False,new_fit=False,public_source_sha256=sha(Path(__file__)))
    text = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (a/'analysis.json').write_text(text,encoding='utf8',newline='\n')
    (ROOT/'analysis/game226-hardware01-verification.json').write_text(text,encoding='utf8',newline='\n')
    (a/'progress.json').write_text(json.dumps(dict(status='hardware60s_pass_scroll_gain_60fps_open',
        next=next_work,fps60=False,new_firmware=False),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(current=current,metrics=metrics),ensure_ascii=False))


if __name__ == '__main__':
    main()
