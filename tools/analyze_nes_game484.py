# SPDX-License-Identifier: MIT
"""Reconcile484 planner attribution/candidate with fixed482 hardware budgets.

No target-instruction to hardware-time conversion. Per-frame records are the
authority for ready events: the first profile02 aggregate reused a mutable list.
Preserve that original and validate/reassemble its immutable frame records.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
from check_nes_game478 import ELFFile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
read = lambda q: json.loads(q.read_text(encoding='utf8'))
p = argparse.ArgumentParser(description=__doc__)
for n in ['base', 'arm', 'profile_base', 'profile', 'reference', 'guards', 'preparation', 'out']:
    p.add_argument('--'+n.replace('_', '-'), required=True, type=Path)
a = p.parse_args()
old = read(ROOT/'analysis/mmc482-verification.json')
before, after, guards, prep = [read(q) for q in [a.profile_base/'result.json', a.profile/'result.json', a.guards/'result.json', a.preparation]]
assert before['passed'] and after['passed'] and guards['passed']
assert sha(a.base/'obj-nes-100/firmware.stm') == old['ARM']['firmware_SHA256'] == before['firmware_SHA256']
assert sha(a.arm/'obj-nes-100/firmware.stm') == after['firmware_SHA256']
assert before['input_SHA256'] == after['input_SHA256']
assert before['E8_prior480_status_counts'] == after['E8_prior480_status_counts']
rows, frame_pins, repaired = [], {}, 0
for b, aggregate in zip(before['frames'], after['frames']):
    q = a.profile/f'frame{b["frame"]}.json'
    f = read(q)
    # All instruction/state data must match the original aggregate. Only the
    # event-list alias is repaired, from records already saved during execution.
    assert {k:v for k,v in f.items() if k!='plan_ready_events'} == {k:v for k,v in aggregate.items() if k!='plan_ready_events'}
    repaired += f['plan_ready_events'] != aggregate['plan_ready_events']
    assert len(f['plan_ready_events']) == f['plan_count']
    assert f['receive_instructions'] == b['receive_instructions']
    assert f['state_SHA256'] == b['state_SHA256']
    assert f['baseline_planner_instructions'] == b['planner_instructions']
    assert f['saved_instructions'] == b['planner_instructions']-f['planner_instructions'] > 0
    frame_pins[q.name] = sha(q)
    events = f['plan_ready_events']
    plans = read(a.reference/f'frame{b["frame"]}.json')['candidate']['plans']
    assert len(plans) == len(events)
    lengths = []
    for (_, encoded), event in zip(plans, events):
        raw = bytes.fromhex(encoded)
        assert len(raw) == 40 and raw[6] == event['kind']
        alts = [int.from_bytes(raw[i:i+2], 'little') for i in range(24, 40, 2)]
        canonical = raw[8:24] == bytes(i//2 for i in range(16)) and all(v==65535 for v in alts)
        lengths.append(3 if raw[6]>=2 else (7+raw[6] if canonical else 16+2*sum(v!=65535 for v in alts)))
    # Projection of unchanged append()/finish(), not a target SPI schedule.
    # Include END, which is appended only after the planner returns.
    def batches(early):
        count = size = sent = 0
        first = None
        for i, n in enumerate(lengths+[3]):
            prefix = events[i]['prefix_instructions'] if i<len(events) else f['planner_instructions']
            if count==15 or size+n>240:
                sent += 1; first = prefix if first is None else first; count = size = 0
            count += 1; size += n
            if count==15 or (early and i<len(events) and events[i]['kind']==0):
                sent += 1; first = prefix if first is None else first; count = size = 0
                early = False
        if count:
            sent += 1; first = f['planner_instructions'] if first is None else first
        return {'E9_packets': sent, 'first_E9_ready_prefix': first}
    normal, early = batches(False), batches(True)
    rows.append({'frame': f['frame'], 'before': b['planner_instructions'], 'after': f['planner_instructions'],
                 'saved': f['saved_instructions'], 'plan_count': f['plan_count'],
                 'first_ready': events[0]['prefix_instructions'],
                 'first_BG_ready': next((e['prefix_instructions'] for e in events if e['kind']==0), None),
                 'last_BG_ready': next((e['prefix_instructions'] for e in reversed(events) if e['kind']==0), None),
                 'last_ready': events[-1]['prefix_instructions'], 'state_SHA256': f['state_SHA256']})
    rows[-1]['append_policy_projection'] = {'unchanged': normal, 'first_BG_flush': early,
        'additional_E9_packets': early['E9_packets']-normal['E9_packets'],
        'additional_E9_framing_bytes': 8*(early['E9_packets']-normal['E9_packets']),
        'new_flush_poll_charge_bytes_before_replaced_polls': 20*(early['E9_packets']-normal['E9_packets'])}
assert len(rows) == 71 and [q['frame'] for q in rows] == list(range(905, 976))
assert sum(q['after'] for q in rows) == after['planner_instructions']
assert sum(q['before'] for q in rows) == before['planner_instructions']
assert sum(q['saved'] for q in rows) == after['saved_instructions']
# Allocated object sections AND link relocations pin actual executable inputs.
# .stabstr may contain assembler temporary names; retain separate raw hashes.
objects = {}
for q in (a.base/'obj-nes-100').rglob('*.o'):
    n = q.relative_to(a.base/'obj-nes-100')
    dest = a.arm/'obj-nes-100'/n
    with q.open('rb') as x, dest.open('rb') as y:
        xelf, yelf = ELFFile(x), ELFFile(y)
        def sections(e):
            return {s.name: hashlib.sha256(s.data()).hexdigest() for s in e.iter_sections()
                    if s['sh_flags'] & 2 or (s['sh_type'] in ['SHT_REL', 'SHT_RELA'] and not s.name.startswith('.rel.debug'))}
        xs, ys = sections(xelf), sections(yelf)
    objects[n.as_posix()] = {'baseline_raw_SHA256': sha(q), 'candidate_raw_SHA256': sha(dest),
                            'allocated_or_relocation_changed': xs != ys}
changed = [n for n,v in objects.items() if v['allocated_or_relocation_changed']]
assert sorted(changed) == ['nes_planner211.o', 'nes_resident211.o'], changed
size = (a.arm.parent/'size.log').read_text(encoding='utf8').splitlines()[1].split()
text, data, bss = map(int, size[:3])
assert data == old['ARM']['data'] and bss == old['ARM']['BSS']
firmware_bytes = (a.arm/'obj-nes-100/firmware.stm').stat().st_size
saved = sum(q['saved'] for q in rows)
r = {'passed': True, 'candidate': 484, 'scope': __doc__, 'physical_baseline': 'MMC482',
     'merged_PR135': '948a2e9bc6542aaec7737e28f4431cb0c0350f6d',
     'state_and_40B_plans_equal': True, 'receiver_instructions_unchanged': True,
     'frames': rows, 'before_instructions': before['planner_instructions'], 'after_instructions': after['planner_instructions'],
     'saved_instructions': saved, 'saved_percent': 100*saved/before['planner_instructions'],
     'median_before': statistics.median(q['before'] for q in rows),
     'median_after': statistics.median(q['after'] for q in rows),
     'minimum_frame_saving_percent': min(100*q['saved']/q['before'] for q in rows),
     'maximum_frame_saving_percent': max(100*q['saved']/q['before'] for q in rows),
     'exclusive_functions_before': before['exclusive_functions'], 'exclusive_functions_after': after['exclusive_functions'],
     'warm_plan_count_below15': sum(q['plan_count']<15 for q in rows[2:]), 'warm_frames': len(rows[2:]),
     'projected_warm_first_E9_at_finish': sum(q['append_policy_projection']['unchanged']['first_E9_ready_prefix']==q['after'] for q in rows[2:]),
     'projected_first_BG_extra_E9_packets': sum(q['append_policy_projection']['additional_E9_packets'] for q in rows),
     'prior480_E8_status_counts': before['E8_prior480_status_counts'],
     'supply_gate': 'Small batches may wait until finish; ready prefixes alone do not prove E9 transmission or overlap. Bulk op7 holds exchange through actual consume/ACK. Compare early batching with descriptor backpressure, additional SPI and unchanged ROM phase.',
     'guards': {'output': guards['output'], 'full_resident_index_state': guards['full_resident_index_state_compared'],
                'scope': guards['scope']},
     'ARM': {'firmware_SHA256': after['firmware_SHA256'], 'ELF_SHA256': after['ELF_SHA256'],
             'bytes': firmware_bytes, 'text': text, 'data': data, 'BSS': bss,
             'text_delta': text-old['ARM']['text'], 'Flash_tail': old['ARM']['Flash_tail']-(firmware_bytes-old['ARM']['bytes']),
             'RUN_workspace': old['ARM']['RUN_workspace'], 'new_allocation_bytes': 0, 'full_stack_proof': False},
     'object_count': len(objects), 'changed_executable_objects': changed, 'object_inputs': objects,
     'baseline_source_SHA256': prep['baseline_sources'], 'candidate_source_SHA256': prep['patch_sources'],
     'FPGA': {'changed': False, 'new_Quartus_run': False, 'reused482_FIT': old['FIT'], 'remaining_LE': old['remaining_LE'],
              'scope': '482 bitstream unchanged; this ARM candidate was not jointly timed or physically tested'},
     'evidence_SHA256': {'profile_baseline': sha(a.profile_base/'result.json'), 'profile_candidate_original': sha(a.profile/'result.json'),
                         'guards': sha(a.guards/'result.json'), 'preparation': sha(a.preparation)},
     'candidate_frame_SHA256': frame_pins, 'raw_aggregate_event_alias_repaired_frames': repaired,
     'physical_FPS': None, 'full_path_ms': None, 'delivery_ready': False,
     'limits': ['Target instructions are not hardware cycles; no21.38% FPS claim',
                'Historical71 game snapshots, host encoder/SPI and immediate writer completion; no actual runtime IRQ/ROM/65816 timeline',
                'Unit128KiB RAM does not prove physical SRAM/stack headroom',
                'Prior480 E8 bytes classify23 replies; not482 physical89-polls-per-display attribution or durations',
                '60Hz and the51.8168ms mean physical gap remain open; receive17.1571ms and SEAL18.4430ms also require work',
                'Existing raw reset/CDC/IO limitations remain; no new ZIP or hardware trial']}
a.out.write_text(json.dumps(r, indent=2)+'\n', encoding='utf8')
print(json.dumps({k:r[k] for k in ['passed','before_instructions','after_instructions','saved_percent','median_before','median_after','changed_executable_objects','raw_aggregate_event_alias_repaired_frames']}))
