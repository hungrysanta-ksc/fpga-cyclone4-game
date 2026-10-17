# SPDX-License-Identifier: MIT
"""Preserve hardware210 evidence and cross-check bounded budget accounting.

Read-only source analysis: no firmware build, inferred scene labels or FPS claim.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
from analyze_nes_budget210 import analyze, FIELDS
from decode_nes_minreject180 import decode

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
WIRE = 'ingress e8 e9 e0 e1 other'.split()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    raw = a.out / 'raw'
    raw.mkdir()
    hashes = {}
    for kind in ['progress', 'game-last', 'budget']:
        name = f'nes-{kind}-210.txt'
        shutil.copyfile(a.inputs / name, raw / name)
        assert sha(a.inputs / name) == sha(raw / name)
        hashes[name] = dict(bytes=(raw / name).stat().st_size, sha256=sha(raw / name))
    text = (raw / 'nes-game-last-210.txt').read_text(encoding='utf-8-sig')
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    fields = dict(x.split('=', 1) for x in lines)
    assert len(fields) == len(lines)
    stages = [dict(re.findall(r'(\w+)=(\S+)', x)) for x in
              (raw / 'nes-progress-210.txt').read_text().splitlines() if x.strip()]
    assert [int(x['seq']) for x in stages] == list(range(100))
    by = {x['stage']: x for x in stages}
    assert fields['candidate'] == 'NES-GAME-210'
    assert all(fields[k] == '0' for k in ['verify_error', 'run_error', 'run_rom_error',
        'run_first_error', 'run_stop_error', 'native_receiver_error', 'native_sink_error',
        'sink_window_error', 'trace_aborts'])
    assert all(fields[k] == '1' for k in ['verified', 'run_passed', 'stop_ok',
        'base_restored', 'safe_to_reload', 'spc_unmute_confirmed', 'native_result'])
    assert fields['native_video_error'] == '14' and fields['plan_error'] == '3'
    assert fields['trace_begins'] == fields['trace_ends'] == fields['trace_commits'] == '197'
    assert fields['native_frames'] == '196'
    assert fields['sink_window_sent'] == fields['sink_window_retired'] == '7608'
    assert fields['sink_window_ack'] == '0' and fields['plan_sent'] == '4' and fields['plan_end'] == '0'
    duration = int(by['DISPLAY_STOPPED']['elapsed_ms']) - int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration == 60060
    budget = analyze(raw / 'nes-budget-210.txt')
    assert budget['open_frame'] == 1 and budget['failed_transfers'] == 0
    totals = {k: sum(b[k] for b in budget['bins']) for k in FIELDS if k != 'maxgap'}
    totals['maxgap'] = max(b['maxgap'] for b in budget['bins'])
    clocked = sum(totals[k] for k in WIRE)
    assert clocked == int(fields['native_wire_bytes']) == 7543494
    assert totals['frames'] == int(fields['native_frames'])
    assert totals['plan'] == int(fields['profile_build_stage_ticks'])
    assert totals['seal'] == int(fields['profile_seal_ack_ticks'])
    assert totals['recv'] - int(fields['profile_receive_ticks']) == 2
    assert totals['e8'] % 20 == totals['e0'] % 20 == 0
    assert totals['other'] == totals['frames'] * 7
    for i, row in enumerate(budget['bins']):
        row['contains_terminal_partial_frame'] = i == 11
        row['reuse_output_percent'] = 100 * row['reuse'] / row['out'] if row['out'] else None
        # Counterfactual ONLY: removes E8/E0, not other D0-D3 control or actual waits.
        row['remove_e8_e0_only_wire_ms_per_completion'] = (
            row['clocked_bytes'] - row['e8'] - row['e0']) * 8000 / 2625000 / row['frames']
    n = totals['frames']
    now = dict(duration_ms=duration, display_completed=n,
        display_completed_per_s=n * 1000 / duration, amortized_display_ms=duration / n,
        receive_ms=int(fields['profile_receive_ticks']) * 10,
        build_stage_ms=int(fields['profile_build_stage_ticks']) * 10,
        seal_ack_ms=int(fields['profile_seal_ack_ticks']) * 10,
        transactions=int(fields['native_transactions']), clocked_bytes=clocked,
        window_packets=int(fields['sink_window_sent']))
    old = ROOT / 'analysis/game209-hardware01-verification.json'
    before = json.loads(old.read_bytes())['comparison']['current209']
    changes = {k: (now[k] / before[k] - 1) * 100 for k in [
        'display_completed_per_s', 'receive_ms', 'build_stage_ms', 'seal_ack_ms',
        'transactions', 'clocked_bytes', 'window_packets']}
    src = BASE / 'probes/nes-budget210/arm03/src'
    names = ['nes_native_runtime165.c', 'nes_plan_service200.c', 'nes_plan191.c',
             'nes_sink_window184.c', 'nes_budget210.c', 'nes_budget210.h']
    prep = json.loads((src.parent / 'preparation-budget210.json').read_bytes())
    pins = prep['copied'] | prep['changed'] | prep['added']
    sources = {k: sha(src / k) for k in names}
    for name, digest in sources.items():
        assert pins['src/' + name] == digest, name
    runtime = (src / names[0]).read_text()
    assert 'if(!s->result)s->result=(uint8_t)reason' in runtime
    assert 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
    assert 'nes_budget210_wire(opcode,n,ok)' in runtime
    status = totals['e8'] + totals['e0']
    metrics = dict(wire_share_percent={k: totals[k] * 100 / clocked for k in WIRE},
        e8_e0_bytes=status, e8_e0_wire_percent=status * 100 / clocked,
        e8_calls=totals['e8'] // 20, e0_calls=totals['e0'] // 20,
        pure_counted_wire_seconds=clocked * 8 / 2625000,
        model_reuse_output_percent=totals['reuse'] * 100 / totals['out'],
        model_reuseplan_percent_of_clocked=totals['reuseplan'] * 100 / clocked,
        remove_e8_e0_only_whole_run_ms_per_completion=(clocked-status)*8000/2625000/n,
        max_completion_gap_ms=totals['maxgap'] * 10)
    result = dict(candidate=210, raw_inputs=hashes, fields=fields, stages=stages,
        source_pins=sources, episodes=decode(text), budget=budget, totals=totals, metrics=metrics,
        comparison=dict(before209=before, current210=now, change_percent=changes,
            baseline_sha256=sha(old), controlled=False,
            scope='Different scenes/inputs and passive measurement cost. Whole-run display completions, not scrolling FPS or CRT refresh.'),
        hardware=dict(user_report='소리 정상, 메뉴 복귀도 성공이야. 프레임은 여전했던거 같아.',
            sound_normal=True, visible_menu_restored=True, frame_improvement_confirmed=False,
            control='not separately confirmed this turn', scene_times='not supplied; clarification pending',
            video_provided=False, fps60=False),
        terminal=dict(primary='deadline1', duration_ms=duration, last_display_ms=59870,
            last_display_generation=262, producer_commits=197, displayed=196,
            plan_error=3, video_error=14, underlying_failed_transfers=0,
            explanation='Deadline pre/post transfer guard can return false while underlying transfer failure count stays zero; plan callback3 propagates to video14. Consistent with normal deadline interruption, not independent CRC/bus-fault evidence. Exact E8/E9 boundary unavailable. Last ACK0 is an in-flight sample, not invalidation of196 completed displays.'),
        limitations=['5s bins use frame START, not completion wall-clock windows or scene labels.',
            'b11 contains a terminal partial frame; exclude it from exact reuseplan subtraction/projections.',
            'Receive totals differ20ms because separate10ms tick samples are taken; do not force equality.',
            'E8/E0 byte fraction is not elapsed-time share or proof that polling causes all delay.',
            'Ingress includes D0-D3 control/polls; E1 includes mixed commands, not map-only useful bytes.',
            'Reuse model is not deployed cache hit rate: no stable slot/bank/base/eviction/CHR-RAM proof.',
            'Plan bytes saved omit possible source/consumer work savings; no net FPS prediction.',
            'Actual PSRAM misses/SNES compare/fallback/VBlank and separate service SPI remain unmeasured.',
            'Last16 pad transitions are incomplete NES-clock records, not a host scene timeline.'],
        next='Use existing210 budget to design persistent physical-pattern slots + scroll-aware map + end-to-end dirty consumption jointly. Retain final display ACK/lease/epoch and active/pending slot protection. Quantify ingress/control and source/SNES work in a bounded replay with the next performance change, not a poll-only or diagnostic-only firmware loop. Require actual scroll scene evidence before claiming scroll improvement. No repeat210/044 requested now.',
        new_package=False, new_fit=False, public_source_sha256=sha(Path(__file__)))
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    (a.out / 'analysis.json').write_text(output, encoding='utf8', newline='\n')
    (ROOT / 'analysis/game210-hardware01-verification.json').write_text(output, encoding='utf8', newline='\n')
    (a.out / 'progress.json').write_text(json.dumps(dict(status='hardware_result_recorded',
        next=result['next'], fps60=False, new_package=False), ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(current=now, metrics=metrics, change_percent=changes), ensure_ascii=False))

if __name__ == '__main__':
    main()
