# SPDX-License-Identifier: MIT
"""Reconcile received482 hardware counters; preserve nested timing and deadline semantics."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--raw', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
names = {k: f'nes-{k}-mmc482.txt' for k in ['progress', 'budget', 'game-last']}
raw = {k: (a.raw/n).read_text(encoding='utf-8-sig').replace('\0', '') for k, n in names.items()}
fields = lambda s: {k: v.strip() for k, v in re.findall(r'^([a-zA-Z0-9_]+)=(.*?)\s*$', s, re.M)}
g, b = fields(raw['game-last']), fields(raw['budget'])
expected = {'candidate':'NES-MMC482', 'board_expected_hex':'7b', 'board_observed_hex':'7b',
            'board_seen':'1', 'load_result':'0', 'file_result':'0', 'end_accepted':'1',
            'loaded_bytes':'393216', 'compared_bytes':'393216', 'verified':'1', 'verify_error':'0',
            'start_sent':'1', 'run_passed':'1', 'run_error':'0', 'run_first_error':'0', 'run_stop_error':'0',
            'run_rom_error':'0', 'run_flags':'1', 'screen_status_valid':'1', 'screen_stage':'3',
            'stop_ok':'1', 'base_restored':'1', 'safe_to_reload':'1',
            'menu_state':'PREPARED_RESET_HELD', 'native_result':'1', 'native_receiver_error':'0',
            'native_video_error':'0', 'trace_aborts':'0', 'plan_error':'0'}
for k, v in expected.items():
    assert g[k] == v, (k, g[k])
for k, v in {'cost_schema':'474', 'cost_counter_available':'1', 'cost_clock_hz':'84000000',
             'cost_scene_crc32_hex':'5a04eed7', 'cost_crc_errors':'0', 'cost_transfer_stops':'0',
             'failed_transfers':'0', 'boot_reason':'1', 'boot_ticks':'5'}.items():
    assert b[k] == v, (k, b[k])
records = [(int(seq), stage, int(ms)) for seq, stage, ms in re.findall(r'MMC482 seq=(\d+) stage=(\S+).*?elapsed_ms=(\d+)', raw['progress'])]
assert [x[0] for x in records] == list(range(100))
assert all(x[2] <= y[2] for x, y in zip(records, records[1:]))
marks = {stage: ms for _, stage, ms in records}
seconds = (marks['DISPLAY_STOPPED']-marks['DISPLAY_NEXT'])/1000
n = int(g['native_frames'])
assert n == 877 and seconds == 60.06
columns = b['columns'].split(',')
bins = []
for index, line in re.findall(r'^b(\d+)=(.*)$', raw['budget'], re.M):
    values = [int(x, 16) for x in line.split(',')]
    assert len(values) == len(columns) == 23
    bins.append({'index': int(index), **dict(zip(columns, values))})
assert [x['index'] for x in bins] == list(range(12))
total = {k: (max if k == 'maxgap' else sum)(r[k] for r in bins) for k in columns}
assert total['frames'] == n
assert total['plan'] == total['planner_ticks']+total['begin_ticks']+total['finish_ticks']
for k, name in [('recv','receive'), ('plan','build_stage'), ('seal','seal_ack')]:
    assert total[k] == int(g[f'profile_{name}_ticks'])
clock, spi = 84000000, 2625000
def bucket(key, name):
    calls, size, hi, lo, maximum = map(int, b[key].split(','))
    cycles = (hi << 32) | lo
    return {'name': name, 'calls': calls, 'bytes': size, 'cycles': cycles,
            'mean_ms_per_completed_display': cycles/clock*1000/n,
            'max_interval_ms': maximum/clock*1000,
            'ideal_wire_ms_per_display': size*8/spi*1000/n}
ops = [bucket(f'cost_op_{i:02d}', name) for i, name in enumerate(b['cost_op_order'].split(','))]
phases = [bucket(f'cost_phase_{i:02d}', name) for i, name in enumerate(['receive', 'plan_supply', 'seal_final_ack'])]
assert ops[1]['calls'] == ops[2]['calls']
assert ops[3]['calls'] == int(g['trace_commits']) == int(g['trace_ends']) == phases[1]['calls'] == n+1
assert ops[8]['calls'] == phases[2]['calls'] == n
assert int(g['trace_generation']) == int(g['native_generation'])+1
for i, key in [(4,'e0'), (5,'e1'), (6,'e8'), (7,'e9'), (8,'other')]:
    assert ops[i]['bytes'] == total[key]
assert sum(x['bytes'] for x in ops[:4]) == total['ingress']
assert sum(total[k] for k in ['ingress','e0','e1','e8','e9','other']) == int(g['native_wire_bytes'])
assert sum(x['bytes'] for x in ops) == int(g['native_wire_bytes'])+ops[9]['bytes']+ops[10]['bytes']
assert sum(x['calls'] for x in ops) == int(g['native_transactions'])+ops[9]['calls']+ops[10]['calls']
waits = []
for i, name in enumerate(b['cost_poll_order'].split(',')):
    calls, progress, quiet, hi, lo, maximum = map(int, b[f'cost_poll_{i}'].split(','))
    assert calls == progress+quiet
    waits.append({'name': name, 'calls': calls, 'progress': progress, 'quiet': quiet,
                  'completed_quiet_ms_per_display': ((hi << 32) | lo)/clock*1000/n})
assert ops[4]['calls']-sum(x['calls'] for x in waits) == 1
assert int(g['sink_window_sent']) == int(g['sink_window_retired'])
assert ops[5]['calls']-int(g['sink_window_sent']) == 1
assert g['native_sink_error'] == '2' and g['sink_window_error'] == '3' and g['sink_trace_ack_valid'] == '0'
flags = int(b['boot_last_hex'][2:4], 16)
assert b['boot_last_hex'] == '01fca903' and g['spc_init_status_valid'] == '1' and g['spc_unmute_confirmed'] == '1'
groups, reused = int(b['cost_group_total']), int(b['cost_group_reused'])
assert groups == 26340 and reused == 2243
baseline = json.loads((ROOT/'analysis/receive477-hardware.json').read_text(encoding='utf8'))
build = json.loads((ROOT/'analysis/mmc482-verification.json').read_text(encoding='utf8'))
package = json.loads((ROOT/'analysis/mmc482-package.json').read_text(encoding='utf8'))
ms = seconds*1000/n
sources = ROOT.parent/'probes/nes-mmc482/executed/ARM01/src'
source_pins = {k: sha(sources/k) for k in ['nes_native_runtime165.c','nes_plan_service200.c','nes_sink_window184.c','nes_budget210.c','nes_cost471.c']}
run = {'display': {'seconds': seconds, 'completed': n, 'fps': n/seconds, 'mean_ms': ms,
                   'bins5s_counts_by_frame_start': [r['frames'] for r in bins], 'p95_ms': None},
       'progress_ms': marks, 'boot': {'ticks10ms': 5, 'ms': 50, 'polls': int(b['boot_polls']),
                                     'first_hex': b['boot_first_hex'], 'last_hex': b['boot_last_hex'],
                                     'flags': flags, 'qualified_vector_flags': flags & 3,
                                     'qualified_program_read': bool(flags & 4), 'spc_status_hex': 'a9'},
       'DWT_inclusive_phases': phases, 'DWT_op_buckets': ops, 'quiet_buckets': waits,
       'coarse_totals': total, 'coarse_ms_per_display': {
           'planner_excluding_callbacks_estimate': (total['planner_ticks']-total['callback_ticks'])*10/n,
           'callbacks': total['callback_ticks']*10/n, 'begin': total['begin_ticks']*10/n,
           'finish': total['finish_ticks']*10/n},
       'group_reuse': {'total': groups, 'reused': reused, 'fraction': reused/groups,
                       'NROM476_fraction': baseline['runs'][0]['group_reuse']['fraction']},
       'SPI': {'native_bytes': int(g['native_wire_bytes']), 'native_transactions': int(g['native_transactions']),
               'configured_clock_hz': spi, 'fixed_observed_traffic_ideal_ms_per_display': int(g['native_wire_bytes'])*8/spi*1000/n,
               'E0_plus_E8_inclusive_ms_per_display': ops[4]['mean_ms_per_completed_display']+ops[6]['mean_ms_per_completed_display']},
       'termination': {'deadline': True, 'input_commits': n+1, 'final_ACK_and_EA': n,
                       'window_sent': int(g['sink_window_sent']), 'window_retired': int(g['sink_window_retired']),
                       'E1_transfers': ops[5]['calls'], 'one_transfer_not_bookkept_after_post_IO_deadline_guard': True,
                       'final_physical_packet_accept_or_display_confirmed': False, 'STOP_base_menu_ok': True},
       'targets': {'mean_ms_gap_to30fps': ms-1000/30, 'mean_ms_gap_to60Hz': ms-1000/60,
                   'latency_reduction_fraction_to60Hz': 1-(1000/60)/ms}}
r = {'passed': True, 'receipt': 483, 'trial': 482, 'trial_family': 'MMC', 'hardware_run_passed': True, 'runs': [run],
     'raw_SHA256': {n: sha(a.raw/n) for n in names.values()}, 'source_pins': source_pins,
     'intended_artifacts': {'firmware_SHA256': build['ARM']['firmware_SHA256'], 'FPGA_BI3_SHA256': build['FPGA']['BI3_SHA256'], 'ZIP_SHA256': package['ZIP_SHA256']},
     'hardware_attestation': 'user installation, profile7b, strict ROM CRC and log identity consistent; no on-chip image SHA readback',
     'user_observation': {'execution_succeeded': True, 'menu_return_normal': True, 'video_supplied': False},
     'limits': ['One interactive SMB3 run; not a same-scene speedup over NROM476', '480 root cause is not isolated by one482 success',
                'DWT phase/op/quiet are nested and must not be added or all subtracted as savings',
                '10ms coarse planner/callback counters are estimates, not precise CPU cycle attribution',
                'Bins are assigned by frame START, not exact scene or completion timestamps',
                'SPI wire figure assumes fixed observed traffic; not an impossibility proof after polling changes',
                'screen_frames0/phase_mask0 are legacy telemetry; counted display evidence is final ACK/EA877',
                'SPC A9 is an init result, not run_error; no audible-audio proof from this receipt',
                'Capture-loss, per-frame p95, exact VBlank/ROM phase and NES real-time emulation speed remain unmeasured'],
     'next_order': ['Keep482 as physical game baseline; profile actual M4 planner on representative game packets and separate E8 descriptor/busy/credit/finish outcomes',
                    'Compare combined ARM planner and source/tile supply schedule using the same482 RTL, SPI/IRQ/credit/STOP/finalACK',
                    'Reduce validated redundant E8/E0 traffic and waits; preserve required response validation and DMA/receipt ownership',
                    'Include input17ms and VBlank scheduling in whole-time budget before claiming60Hz; then a controlled same-ROM hardware comparison'],
     'no_new_build_or_FIT': True, 'scope': __doc__}
a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps({'passed': True, 'fps': n/seconds, 'phase_ms': [x['mean_ms_per_completed_display'] for x in phases],
                  'coarse_ms': run['coarse_ms_per_display'], 'SPI_ideal_ms': run['SPI']['fixed_observed_traffic_ideal_ms_per_display']}))
