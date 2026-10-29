# SPDX-License-Identifier: MIT
"""Bind the real480 failure logs and supplied ROM identity; never infer FPS."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zlib

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--logs', required=True, type=Path)
p.add_argument('--rom', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def fields(name):
    text = (a.logs/name).read_text(encoding='utf-8-sig').replace('\0', '')
    return dict(re.findall(r'^([a-zA-Z0-9_]+)=(.*?)\s*$', text, re.M))
game = fields('nes-game-last-mmc480.txt')
budget = fields('nes-budget-mmc480.txt')
data = a.rom.read_bytes()
assert len(data) == 0x60010 and sha(a.rom) == 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
assert data[:16].hex() == '4e45531a101042000000000000000000'
expected = {'load_result': 0, 'file_result': 0, 'loaded_bytes': 393216, 'compared_bytes': 393216,
            'verify_error': 0, 'verified': 1, 'end_accepted': 1, 'stop_ok': 1,
            'base_attempted': 1, 'base_restored': 1, 'safe_to_reload': 1,
            'start_sent': 1, 'run_passed': 0, 'run_error': 6, 'run_rom_error': 0,
            'run_stop_error': 0, 'screen_status_valid': 1, 'screen_stage': 0,
            'screen_flags': 0, 'screen_frames': 0, 'native_result': 2, 'native_frames': 0}
assert all(int(game[k]) == v for k, v in expected.items())
boot = {k: budget[k] for k in ['startup_reason', 'startup_post_reason', 'startup_signals_hex',
                              'boot_schema', 'boot_reason', 'boot_polls', 'boot_ticks',
                              'boot_first_hex', 'boot_last_hex', 'boot_signals_hex']}
assert int(boot['boot_reason']) == 5 and int(boot['boot_ticks']) == 500
progress = (a.logs/'nes-progress-mmc480.txt').read_text(encoding='utf-8-sig')
events = [{'sequence': int(seq), 'stage': stage, 'elapsed_ms': int(ms)}
          for seq, stage, ms in re.findall(r'MMC480 seq=(\d+) stage=(\S+).*?elapsed_ms=(\d+)', progress)]
last = {e['stage']: e for e in events}
stages = [last[k] for k in ['DISPLAY_NEXT', 'DISPLAY_STOPPED', 'STOP_DONE', 'MENU_PREPARED']]
r = {'candidate': 'MMC480', 'hardware_run_passed': False, 'physical_FPS': None,
     'ROM': {'bytes': len(data), 'SHA256': sha(a.rom), 'CRC32': f'{zlib.crc32(data):08x}',
             'header_hex': data[:16].hex(), 'matches_selected_target': True},
     'log_SHA256': {n: sha(a.logs/n) for n in ['nes-game-last-mmc480.txt', 'nes-budget-mmc480.txt', 'nes-progress-mmc480.txt']},
     'hardware_fields': expected, 'boot': boot, 'final_stages': stages,
     'display_attempt_ms': last['DISPLAY_STOPPED']['elapsed_ms']-last['DISPLAY_NEXT']['elapsed_ms'],
     'user_observation': 'black screen then normal menu return',
     'failure_boundary': 'SNES client startup wait; before native_frames222/cost471_begin',
     'root_cause_confirmed': False,
     'not_performance_evidence': 'No native frame or measured receive/planner/display phase began; zero counters are not zero processing costs.',
     'model_gap': '480 Mesen boot executes a local SFC; console startup/boot ROM pins were modeled, not a physical cartridge fetch proof.'}
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps({'ROM_matches': True, 'failure_boundary': r['failure_boundary'], 'display_attempt_ms': r['display_attempt_ms'], 'physical_FPS': None}))
