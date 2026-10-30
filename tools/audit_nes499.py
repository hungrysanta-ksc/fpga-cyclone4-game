# SPDX-License-Identifier: MIT
"""Audit selected493 inputs and existing physical evidence; not a new HW test.

No ROM bytes, binaries, license data or private traces are copied to the report.
Hash coverage is not line-by-line review or functional verification coverage.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from decode_nes_minreject180 import decode

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_evidence(text):
    history = decode(text)  # Schema3, including reserved positions and ordering.
    names = {0: 'low_while_pair_pending', 1: 'invalid_low_address_or_lane',
             2: 'high_pair_check_failed', 3: 'extra_sprites',
             4: 'ROM_fault', 5: 'unfinished_pair_at_end'}
    rejects = [r for r in history['events'] if r['event'] == 'REJECT']
    for row in history['events']:
        row['fetch_reasons'] = [name for bit, name in names.items()
                                if row['fetch_errors'] & (1 << bit)]
    return dict(history=history, retained_reject_episodes=len(rejects),
                retained_recovery_episodes=len(history['events'])-len(rejects),
                fetch_error_signatures=dict(Counter(str(r['fetch_errors']) for r in rejects)),
                capture_health_proven=False,
                runtime_success_implies_capture_health=False,
                whole_run_reject_count=None, reject_time_ms=None,
                limitation='Last16 episode transitions, not all frames. Generation is modulo256; no error position. Do not derive a rejection rate or lost milliseconds.')


def run(board, arm, raw):
    baseline = json.loads((ROOT/'analysis/boot493-verification.json').read_text())
    measured = json.loads((ROOT/'analysis/hardware494-mmc493.json').read_text())
    r = measured['runs'][0]
    inventory = []
    for name, expected in baseline['FPGA']['source_inputs'].items():
        p = board/name
        actual = sha(p)
        assert actual == expected, ('493 source mismatch', name)
        inventory.append(dict(path=name, SHA256=actual, bytes=p.stat().st_size,
                              lines=len(p.read_bytes().splitlines())))
    arm_files = sorted(p for p in arm.glob('nes*') if p.is_file())
    # Non-NES entry points and build wiring are part of the ownership boundary.
    hooks = []
    for p in sorted(arm.iterdir()):
        if p.is_file() and p.suffix in ['.c', '.h', '.inc'] and not p.name.startswith('nes'):
            if b'nes_' in p.read_bytes().lower():
                hooks.append(p)
    arm_inventory = [dict(path=p.name, SHA256=sha(p), bytes=p.stat().st_size)
                     for p in arm_files+hooks]
    binary=arm/'obj-nes-100/sd2snes.bin'
    assert sha(binary)==baseline['ARM']['firmware_SHA256'], '493 firmware mismatch'
    log = raw/'nes-game-last-mmc493.txt'
    assert sha(log) == measured['source_files'][log.name]['SHA256']
    cap = capture_evidence(log.read_text(encoding='utf8'))
    hz = 2625000
    budget = dict(target_period_ms=1000/60, target_wire_capacity_B=hz/8/60,
                  display=r['display'], phases=r['DWT_phases_nested'],
                  observed_wire_ms=r['wire_ms_per_display'],
                  query_wire_ms=r['status_queries']['wire_ms_per_display'],
                  nonquery_wire_ms=r['nonquery_wire_projection_ms'],
                  body_wire_ms=r['command_body_wire_ms'],
                  body_B=r['command_body_projection'],
                  required_rate_multiplier=60/r['display']['fps'],
                  nonquery_excess_over_period_ms=r['nonquery_wire_projection_ms']-1000/60,
                  additive_phases_driver_quiet=False,
                  projection_is_universal_lower_bound=False)
    return dict(schema_version=1, audit=499, physical_baseline='MMC493',
                hardware_rate_changed=False, runtime_rewritten=False,
                new_Questa_or_Quartus_run=False, new_installer=False,
                review_scope='Selected493 whole-path boundary/code review plus498 delta; upstream CPU/PPU/APU targeted integration review, not complete formal/line-by-line verification. Historical candidates are not deployed code.',
                source_closure=inventory, ARM_NES_inventory=arm_inventory,
                ARM_NES_files=len(arm_files), ARM_non_NES_hooks=len(hooks),
                ARM_firmware_SHA256=sha(binary),
                ARM_source_inventory_is_not_rebuild_proof=True,
                compiled_NES_translation_units=[p.name for p in sorted((arm/'obj-nes-100').glob('nes*.su'))],
                physical_capture=cap, budget=budget,
                evidence={n:sha(ROOT/n) for n in ['analysis/boot493-verification.json',
                    'analysis/hardware494-mmc493.json','analysis/prefetch498-verification.json',
                    'tools/decode_nes_minreject180.py','tools/decode_nes_reject180.py',
                    'tools/audit_nes499.py','tools/test_nes_audit499.py',
                    'tools/analyze_nes_hardware494.py']},
                raw_log_SHA256=sha(log),
                decision='Fix capture rejection diagnosis before another micro-optimization. Preserve493;498 is not selected. Budget structural transfer/schedule changes before implementation.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['board', 'arm', 'raw', 'out']:
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args()
    assert not a.out.exists(), 'Preserve earlier audit evidence'
    result = run(a.board, a.arm, a.raw)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(source_files=len(result['source_closure']),
        ARM_NES_files=result['ARM_NES_files'], hooks=result['ARM_non_NES_hooks'],
        capture=result['physical_capture']['fetch_error_signatures'],
        budget=result['budget']), ensure_ascii=False))
