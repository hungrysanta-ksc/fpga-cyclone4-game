# SPDX-License-Identifier: MIT
"""Reconcile returned moving NROM471 logs; preserve inclusive timing and alias limits."""
import argparse, json, re
from pathlib import Path
from nes_delta231 import ROOT, BASE, sha

p = argparse.ArgumentParser()
p.add_argument('--raw', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
names = ['nes-progress-nrom471.txt', 'nes-budget-nrom471.txt', 'nes-game-last-nrom471.txt']
data = {n: (a.raw / n).read_text(encoding='utf8') for n in names}
last = dict(x.split('=', 1) for x in data[names[2]].splitlines() if '=' in x)
b = data[names[1]]
fields = dict(x.split('=', 1) for x in b.splitlines() if '=' in x)
columns = fields['columns'].split(',')
bins = []
for m in re.finditer(r'^b(\d+)=(.*)$', b, re.M):
    values = [int(x, 16) for x in m[2].split(',')]
    assert len(values) == len(columns) == 23
    bins.append({'index': int(m[1]), **dict(zip(columns, values))})
assert [x['index'] for x in bins] == list(range(12))
total = {k: (max if k == 'maxgap' else sum)(x[k] for x in bins) for k in columns}
progress = []
for m in re.finditer(r'NROM471 seq=(\d+) stage=(\S+).*?elapsed_ms=(\d+)', data[names[0]]):
    progress.append({'seq': int(m[1]), 'stage': m[2], 'ms': int(m[3])})
assert [x['seq'] for x in progress] == list(range(78))
assert all(x['ms'] <= y['ms'] for x, y in zip(progress, progress[1:]))
marks = {x['stage']: x['ms'] for x in progress}
for k, v in {'candidate': 'NES-NROM471', 'board_observed_hex': '78',
             'loaded_bytes': '393216', 'compared_bytes': '393216', 'verified': '1',
             'verify_error': '0', 'stop_ok': '1', 'base_restored': '1',
             'safe_to_reload': '1', 'run_passed': '1', 'run_error': '0',
             'run_first_error': '0', 'run_stop_error': '0', 'trace_aborts': '0',
             'native_result': '1', 'native_receiver_error': '0',
             'native_video_error': '0'}.items():
    assert last[k] == v, (k, last[k])
for k, v in {'cost_schema': '471', 'cost_clock_hz': '84000000',
             'cost_counter_available': '1', 'cost_scene_crc32_hex': '0fddf31c',
             'cost_crc_errors': '0', 'cost_transfer_stops': '0',
             'failed_transfers': '0'}.items():
    assert fields[k] == v, (k, fields[k])
package = json.loads((ROOT / 'analysis/nrom471-package.json').read_text(encoding='utf8'))
assert fields['cost_scene_crc32_hex'] == package['manifest']['moving_scene_crc32_hex']
n = int(last['native_frames'])
assert total['frames'] == n == 1178
assert total['plan'] == total['planner_ticks'] + total['begin_ticks'] + total['finish_ticks']
for k, name in [('recv', 'receive'), ('plan', 'build_stage'), ('seal', 'seal_ack')]:
    assert total[k] == int(last['profile_' + name + '_ticks'])
wire = sum(total[k] for k in ['ingress', 'e8', 'e9', 'e0', 'e1', 'other'])
assert wire == int(last['native_wire_bytes'])
seconds = (marks['DISPLAY_STOPPED'] - marks['DISPLAY_NEXT']) / 1000
clock, spi = int(fields['cost_clock_hz']), 2625000

def bucket(key, name):
    calls, count, hi, lo, maximum = [int(x) for x in fields[key].split(',')]
    cycles = (hi << 32) | lo
    return {'name': name, 'calls': calls, 'bytes': count, 'cycles': cycles,
            'total_seconds': cycles / clock,
            'mean_ms_per_display': cycles / clock * 1000 / n,
            'max_interval_ms': maximum / clock * 1000,
            'ideal_wire_ms_per_display': count * 8 / spi * 1000 / n}

ops = [bucket('cost_op_' + f'{i:02d}', name) for i, name in enumerate(fields['cost_op_order'].split(','))]
phases = [bucket('cost_phase_' + f'{i:02d}', name) for i, name in enumerate(['receive', 'plan', 'seal'])]
assert sum(x['bytes'] for x in ops[:4]) == total['ingress']
assert ops[4]['bytes'] == total['e0'] and ops[6]['bytes'] == total['e8']
assert ops[5]['calls'] == ops[7]['calls'] == 0
assert ops[11]['bytes'] == total['e1'] + total['e9']
assert sum(x['bytes'] for x in ops) == wire + ops[9]['bytes'] + ops[10]['bytes']
assert sum(x['calls'] for x in ops) == int(last['native_transactions']) + ops[9]['calls'] + ops[10]['calls']
assert int(last['trace_commits']) == int(last['trace_ends']) == ops[3]['calls'] == phases[1]['calls'] == n + 1
assert phases[2]['calls'] == ops[8]['calls'] == n
pending = (int(last['sink_window_sent']) - int(last['sink_window_retired'])) & 65535
assert pending == 1 and last['sink_window_error'] == '3' and last['native_sink_error'] == '2'
# Confirm the observer's OTHER attribution is an input/output alias, not missing packets.
source = BASE / 'probes/nes-nrom418/arm471-04/src'
bulk = (source / 'nes_native165_bulk.inc').read_text(encoding='utf8')
window = (source / 'nes_sink_window184.c').read_text(encoding='utf8')
plan = (source / 'nes_plan_service200.c').read_text(encoding='utf8')
assert bulk.index('bool ok=nes_native165_bulk_inner471') < bulk.index('nes_cost471_op(tx?tx[0]:255')
assert 'io(s,tx,tx,n+3)' in window and re.search(r'transfer\([^;]*\bb,\s*b,', plan)
old = json.loads((ROOT / 'analysis/nrom470-cost.json').read_text(encoding='utf8'))
op_seconds = sum(x['total_seconds'] for x in ops)
op_wire = sum(x['ideal_wire_ms_per_display'] for x in ops)
phase_seconds = sum(x['total_seconds'] for x in phases)
video = json.loads((a.raw / 'video-metadata.json').read_text(encoding='utf8'))
result = {
    'limited_moving_hardware_passed': True, 'trial': 471, 'receipt': 473,
    'intended_artifacts': {'firmware_sha256': package['manifest']['firmware_sha256'],
                           'FPGA_sha256': package['manifest']['FPGA_sha256'],
                           'runtime_attestation': 'user installation/report identity and scene CRC; no on-chip bitstream/firmware hash readback'},
    'input_sha256': {p.name: sha(p) for p in [*(a.raw / x for x in names), a.raw / 'IMG_3721.MOV']},
    'scene': {'kind': 'T1 moving NROM471', 'crc32': fields['cost_scene_crc32_hex'],
              'same_workload_as469': False, 'T0_static471_result': None},
    'user_observation': {'intended_behavior': True, 'menu_return': 'normal'},
    'video_review': {**video, 'sampled_observation': 'blue/red/blue and later red bars; changed bar position visible; menu return from user and progress log',
                     'pixel_exact': False, 'full_frame_loss_proof': False},
    'display': {'window_seconds': seconds, 'completed_frames': n, 'mean_fps': n / seconds,
                'mean_ms': seconds * 1000 / n,
                'last_completed_display_tick_10ms': int(last['profile_last_display_tick']),
                'five_second_bin_completions': [x['frames'] for x in bins],
                'max_gap_tick_10ms': total['maxgap'],
                'steady_max_gap_tick_10ms': max(x['maxgap'] for x in bins[1:]),
                'target_ms_60Hz': 1000 / 60, 'mean_gap_to_60Hz_ms': seconds * 1000 / n - 1000 / 60,
                'frame_level_p95': None, 'fps60_proven': False, 'capture_no_loss_proven': False},
    'DWT_phases_inclusive': phases,
    'DWT_op_buckets': ops,
    'DWT_all_SPI': {'seconds': op_seconds, 'mean_ms_per_display': op_seconds * 1000 / n,
                    'wire_bytes': sum(x['bytes'] for x in ops), 'ideal_wire_ms_per_display': op_wire,
                    'outside_wrapped_SPI_ms_per_display': (seconds - op_seconds) * 1000 / n,
                    'outside_wrapped_SPI_is_pure_ARM_compute': False},
    'DWT_phase_sum_seconds': phase_seconds,
    'outside_successfully_recorded_phases_seconds': seconds - phase_seconds,
    'alias_accounting_issue': {
        'affected': ['E1', 'E9'], 'incorrect_bucket': 'OTHER',
        'cause': 'opcode read after in-place full-duplex transfer overwrote tx[0]',
        'E1_wire_bytes_from_original_budget': total['e1'], 'E9_wire_bytes_from_original_budget': total['e9'],
        'combined_cycles_valid': True, 'split_E1_E9_cycles_valid': False,
        'next_fix': 'snapshot opcode before transfer, preserve471 delivered bytes; add in-place wrapper regression in next candidate'},
    'planner_10ms': {'total_ticks': total['planner_ticks'], 'callback_ticks_nested': total['callback_ticks'],
                     'mean_excluding_callback_ms': (total['planner_ticks'] - total['callback_ticks']) * 10 / n},
    'baseline_context_only': {'scene': 'T0 static428', 'fps': old['display_rate'],
                              'mean_ms': old['mean_ms_per_display'], 'speedup_ratio_claimed': False},
    'termination': {'result': 1, 'first_reason': 'planned6000tick deadline',
                    'input_commits': int(last['trace_commits']), 'display_completions': n,
                    'successful_EA_retires': ops[8]['calls'], 'last_pending_output_packets': pending,
                    'terminal_sink_error': 2, 'terminal_window_error': 3,
                    'interpretation': 'deadline guard cancels final in-flight SEAL/status; no false final display count; STOP/base/menu complete',
                    'receiver_error': 0, 'CRC_errors': 0, 'driver_reported_failed_transfers': 0},
    'raw_counts': total, 'progress_ms': marks,
    'remaining': ['same-scene T0 physical comparison', 'progress/credit/drain/finalACK reason attribution',
                  'warm ARM changed-group/raster reuse with epoch/cold/STOP invalidation',
                  'capture/display timestamp and ownership overlap without premature ACK',
                  '60Hz continuous deadline/p95/miss proof; raw CDC/IO signoff; same-game/MMC4/5'],
    'scope': 'user physical471 moving-scene return, actual DWT and10ms aggregates; no new RTL/build/FIT, no pureCPU/SNES/VBlank phase split or full capture-loss proof'
}
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps({'fps': result['display']['mean_fps'], 'mean_ms': result['display']['mean_ms'],
                  'phase_ms': {x['name']: x['mean_ms_per_display'] for x in phases},
                  'E0_polls_per_display': ops[4]['calls'] / n,
                  'E0_ms': ops[4]['mean_ms_per_display'], 'all_SPI_ms': op_seconds * 1000 / n,
                  'alias_E1_E9_bytes': ops[11]['bytes'], 'CRC_errors': 0, 'menu_return': 'normal'}))
