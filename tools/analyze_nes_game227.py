# SPDX-License-Identifier: MIT
"""Reconcile physical227; retain terminal deadline and uncontrolled scene limits."""
from pathlib import Path
import argparse
import json
import re
from analyze_nes_game213 import ROOT, BASE, sha, fields
from analyze_nes_game226 import COLS, WIRE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    a = parser.parse_args().archive
    assert not (a/'manifest01.json').exists(), 'Sealed evidence is immutable'
    pins = json.loads((a/'inputs.json').read_bytes())
    for name, pin in pins.items():
        assert sha(a/'raw'/name) == pin['sha256']
        assert (a/'raw'/name).stat().st_size == pin['bytes']
    f = fields(a/'raw/nes-game-last-227.txt')
    b = fields(a/'raw/nes-budget-227.txt')
    assert f['candidate'] == 'NES-GAME-227'
    assert f['board_expected_hex'] == f['board_observed_hex'] == '74'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for key in ['verified','end_accepted','start_sent','run_passed','stop_ok',
                'base_restored','safe_to_reload','spc_unmute_confirmed','native_result']:
        assert f[key] == '1', key
    for key in ['load_result','file_result','verify_error','run_error','run_rom_error',
                'run_first_error','run_stop_error','native_sink_error','native_video_error',
                'sink_window_error','trace_aborts','fault_context_valid','plan_error']:
        assert f[key] == '0', key
    assert f['native_receiver_error'] == '24'
    assert f['trace_begins'] == '466'
    assert f['trace_ends'] == f['trace_commits'] == f['native_frames'] == '465'
    assert f['native_generation'] == '657' and f['trace_generation'] == '658'
    assert f['sink_window_sent'] == f['sink_window_retired'] == '13158'
    assert f['sink_window_ack'] == '1' and f['sink_window_flags'] == '2'
    assert f['sink_trace_valid'] == f['sink_trace_ack_valid'] == '0'
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
    assert b['boot_reason'] == '1' and b['boot_polls'] == '444' and b['boot_ticks'] == '5'
    assert b['boot_last_hex'] == '0104a903' and b['plan_valid'] == '0'
    stages = [dict(re.findall(r'(\w+)=(\S+)', line)) for line in
              (a/'raw/nes-progress-227.txt').read_text().splitlines() if line.strip()]
    assert [int(s['seq']) for s in stages] == list(range(100))
    by = {s['stage']:s for s in stages}
    duration = int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration == 60060 and by['MENU_PREPARED']['elapsed_ms'] == '294440'
    bins = []
    for i in range(12):
        values = b[f'b{i:02}'].split(',')
        assert len(values) == len(COLS) and all(len(v) == 8 for v in values)
        row = dict(zip(COLS,(int(v,16) for v in values)))
        assert row['begin_ticks']+row['planner_ticks']+row['finish_ticks'] == row['plan']
        row.update(frame_start_window_s=[5*i,5*(i+1)],terminal_partial=i==11,
                   scene='NO_EXACT_HOST_VIDEO_ALIGNMENT')
        bins.append(row)
    totals = {k:sum(row[k] for row in bins) for k in COLS if k!='maxgap'}
    totals['maxgap'] = max(row['maxgap'] for row in bins)
    wire = sum(totals[k] for k in WIRE)
    assert totals['frames'] == 465 and wire == int(f['native_wire_bytes']) == 7886470
    assert totals['plan'] == int(f['profile_build_stage_ticks']) == 1726
    assert totals['seal'] == int(f['profile_seal_ack_ticks']) == 2057
    assert totals['recv'] == 2164 and int(f['profile_receive_ticks']) == 2163
    assert totals['planner_ticks'] == 736 and totals['callback_ticks'] == 68
    assert totals['begin_ticks'] == 93 and totals['finish_ticks'] == 897
    assert totals['other'] == totals['frames']*7 and totals['e8']%20 == 0
    src = BASE/'probes/nes-repeat227/arm01/src'
    names = ['nes_native_runtime165.c','nes_native_runtime165.h','nes_native165.c',
             'nes_budget210.c','nes_budget210.h','nes_plan_service200.c',
             'nes_planner211.c','nes_native_sink165.c','nes_resident211.c']
    runtime = (src/names[0]).read_text()
    receiver = (src/'nes_native165.c').read_text()
    assert 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
    assert 'if(!s->result)s->result=(uint8_t)reason' in runtime
    assert 'frame(tx,0xd2,tok,0);if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,24);' in receiver
    assert 'return guard(s);' in runtime
    assert 'nes_budget210_time(B226_BEGIN' in runtime and 'nes_budget210_time(B226_FINISH' in runtime
    unchanged = ['nes_native_runtime165.c','nes_native_runtime165.h','nes_native165.c',
                 'nes_budget210.c','nes_budget210.h','nes_plan_service200.c',
                 'nes_planner211.c','nes_resident211.c']
    for name in unchanged:
        assert sha(src/name) == sha(BASE/'probes/nes-fast226/arm01/src'/name), name
    before_path = ROOT/'analysis/game226-hardware01-verification.json'
    old = json.loads(before_path.read_bytes())
    before = old['comparison']['current226']
    current = dict(duration_ms=duration,display_completed=465,
        display_completed_per_s=465000/duration,amortized_display_ms=duration/465,
        receive_ms=21630,receive_bin_ms=21640,build_stage_ms=17260,seal_ack_ms=20570,
        planner_inclusive_ms=7360,callback_ms=680,planner_minus_callback_ms=6680,
        build_outside_planner_ms=9900,begin_ms=930,finish_ms=8970,
        transactions=int(f['native_transactions']),clocked_bytes=wire,window_packets=13158)
    per = {k:dict(before226=old['totals'][k]/452,current227=totals[k]/465,
                  change_percent=(totals[k]/465/(old['totals'][k]/452)-1)*100)
           for k in COLS if k not in ['frames','maxgap']}
    metrics = dict(per_completion=per,count_change_percent=(465/452-1)*100,
        d1_encoded_wire_ms_per_completion=totals['d1_payload']*8000/2625000/465,
        counted_wire_ms_per_completion=wire*8000/2625000/465,
        max_display_gap_ms=totals['maxgap']*10,e8_status_queries=totals['e8']//20,
        middle_bins_04_09=dict(frames=sum(row['frames'] for row in bins[4:10]),
            window_seconds=30,completion_range_per_5s=[29,34],
            caution='Likely first-level-dominated from video, not exact scene alignment or unique CRT frames.'))
    next_work = ('Retain227 correctness but mark scrolling60fps unmet. Do not expand OAM codecs or '
        'repeat227/044. Prioritize geometry ingress and map/metadata egress repetition and finish/drain '
        'as a joint end-to-end16.67ms design: current D1 encoded bytes alone average17.88ms/completion; '
        '20-50s bins D1~19.3..19.8ms and E0/E1~31.7..35.8ms. Evaluate immutable delta/reuse or '
        'existing parallel-aperture delivery with bandwidth/resource/lifetime proof before newFIT; '
        'avoid relocating the same SPI roundtrip. Preserve epoch, row-alt/mask, inactive-bank union, '
        'finalACK/commonSTOP, future mapper semantics, ARM1800B, saveSRAM/GBC164. Minimum meaningful '
        'boundary tests then actual first-level scroll; no assumed clock increase or FPS claim.')
    result = dict(candidate=227,evidence_checks_passed=True,raw_inputs=pins,
        fields=f,budget_fields=b,stages=stages,bins=bins,totals=totals,metrics=metrics,
        comparison=dict(before226=before,current227=current,controlled=False,baseline_sha256=sha(before_path)),
        terminal=dict(primary='deadline1',secondary='receiver24 D2 callback-false OR invalid status',
            last_display_ms=59990,pending_generation=658,displayed_generation=657,
            packets_sent=13158,packets_retired=13158,
            interpretation='Runtime preserves first deadline failure. D2 may be refused before transfer or fail its post-transfer guard; raw D2 response is absent. No independent CRC/status corruption established. Next geometry began but did not COMMIT; all previous display windows retired.'),
        hardware=dict(user_frame_gain_suspected=True,user_scroll_gain_small=True,
            user_sound_normal=True,user_menu_normal=True,user_input_explicitly_reported=False,
            fps60_proven=False,scroll_performance_acceptance=False),
        video=dict(file='IMG_3712.MOV',duration_s=65.33,
            method='131 FFmpeg2fps samples;66one-second samples visually reviewed on4contact sheets',
            events_video_seconds=[['0-4','opening'],['5-7','title/player selection'],
                ['8-12','world map'],['13-14','first-level transition'],
                ['15-54','first level; scrolling visible18-22,25-33,43-52'],
                ['55','exit transition'],['56-60','world map'],
                ['61-62','world map held before menu'],['63-65','cartridge menu']],
            exact_host_alignment=False,audio_reviewed=False,
            notes='Scene samples only; cannot measure unique displayFPS. Audio normal per user. CRT/camera bands/colors are not corruption evidence.'),
        source_pins={str((src/name).relative_to(BASE)).replace(chr(92),'/'):sha(src/name) for name in names},
        unchanged_vs226=unchanged,
        findings=['60.06s/465display completions versus226452: +2.88% count, not controlledFPS; user reports only small scrolling gain.',
            'E1 bytes/completion fall15.13%, SEAL time/completion5.28%; consistent with cheaper egress but objectcount/completion also falls46.63%, so exact OAM causal gain is unmeasured.',
            'Actual tile output/completion rises22.08%, plans17.50%, finish time9.68%; scene differences and source/drain work offset some savings, not proof of regression.',
            'Receive21.63s/build17.26s/SEAL20.57s remain; BEGIN0.93/planner7.36/finish8.97 sum build exactly in every bin.',
            'Middle bins20-50s have29..34completed displays per5s. D1-only bytes exceed16.67ms, while E0/E1 adds31.7..35.8ms percompletion; smallOAM savings cannot establish60fps.'],
        limitations=['10ms timers, receive bins2164 vs profile2163 reflect separately sampled calls.',
            'E1 mixes map, palette, OAM and controls; no live op8 count or section-byte breakdown exists.',
            'Frames count final displayACK, not NES internalFPS or measuredCRT unique frames. 5s bins use frame start and include boundary spill.',
            'Terminal partial receive is not fully timed. Phase totals are not an exhaustive wall-time partition.',
            'Wire excludes direct aperture DMA and separate audio/service; E8 is not PSRAM misses or pure wait.',
            'Different scene duration/inputs/prepared generations prevent a controlled226vs227 speedup claim.'],
        next=next_work,new_firmware=False,new_fit=False,public_source_sha256=sha(Path(__file__)))
    text = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (a/'analysis.json').write_text(text,encoding='utf8',newline='\n')
    (ROOT/'analysis/game227-hardware01-verification.json').write_text(text,encoding='utf8',newline='\n')
    (a/'progress.json').write_text(json.dumps(dict(status='hardware60s_pass_small_gain_scroll60fps_unmet',
        next=next_work,fps60=False,new_firmware=False),ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(current=current,metrics=metrics),ensure_ascii=False))


if __name__ == '__main__':
    main()
