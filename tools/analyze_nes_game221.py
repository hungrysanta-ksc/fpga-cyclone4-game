# SPDX-License-Identifier: MIT
"""Preserve NES221 READY timeout separately from unstarted performance work."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from analyze_nes_game213 import ROOT, BASE, sha, fields


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    raw = a.out / 'raw'
    raw.mkdir()
    pins = {}
    for kind in ['progress', 'game-last', 'budget']:
        name = f'nes-{kind}-221.txt'
        shutil.copyfile(a.inputs / name, raw / name)
        assert sha(a.inputs / name) == sha(raw / name)
        pins[name] = dict(bytes=(raw / name).stat().st_size, sha256=sha(raw / name))
    f = fields(raw / 'nes-game-last-221.txt')
    b = fields(raw / 'nes-budget-221.txt')
    stages = [dict(re.findall(r'(\w+)=(\S+)', x)) for x in
              (raw / 'nes-progress-221.txt').read_text().splitlines() if x.strip()]
    assert [int(x['seq']) for x in stages] == list(range(100))
    by = {x['stage']: x for x in stages}
    assert f['candidate'] == 'NES-GAME-221'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for k in ['verified', 'end_accepted', 'start_sent', 'stop_ok', 'base_restored',
              'safe_to_reload', 'screen_status_valid']:
        assert f[k] == '1', k
    for k in ['verify_error', 'run_rom_error', 'run_stop_error', 'run_passed',
              'screen_stage', 'screen_flags', 'screen_frames', 'native_frames',
              'native_transactions', 'native_wire_bytes', 'trace_begins', 'trace_ends',
              'trace_commits', 'plan_error', 'plan_sent', 'sink_window_sent', 'sink_window_retired']:
        assert f[k] == '0', k
    assert f['run_error'] == f['run_first_error'] == '6' and f['native_result'] == '2'
    assert f['menu_state'] == 'PREPARED_RESET_HELD'
    assert b['budget_schema'] == '221' and b['open'] == b['failed_transfers'] == '0'
    assert b['boot_reason'] == '5' and b['boot_ticks'] == '500' and b['boot_polls'] == '44820'
    assert b['boot_first_hex'] == b['boot_last_hex'] == '01000000'
    assert b['boot_signals_hex'] == '00000606' and b['plan_valid'] == '0'
    columns = b['columns'].split(',')
    assert len(columns) == 21
    for i in range(12):
        values = b[f'b{i:02}'].split(',')
        assert len(values) == len(columns) and all(int(x, 16) == 0 for x in values)
    elapsed = int(by['DISPLAY_STOPPED']['elapsed_ms']) - int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert elapsed == 5020
    selected = BASE / 'probes/nes-index221'
    old = BASE / 'probes/nes-status220'
    names = ['nes_run136.inc', 'nes_runtime_board165.inc', 'nes_boot214.inc', 'nes_boot214.h',
             'nes_cf86_session094.c', 'nes_rom_verify.c', 'nes_rom_spi.c', 'nes_menu_return.c']
    sources = {}
    for name in names:
        before, after = old / 'arm01/src' / name, selected / 'arm01/src' / name
        assert sha(before) == sha(after), name
        sources[name] = dict(before_sha256=sha(before), after_sha256=sha(after), identical=True)
    boot = (selected / 'arm01/src/nes_boot214.inc').read_text()
    assert 'nes_boot214.reason=NES_BOOT214_TIMEOUT' in boot and '>=500u' in boot
    runtime = (selected / 'arm01/src/nes_runtime_board165.inc').read_text()
    assert runtime.index('if(!native_boot172(io))') < runtime.index('nes_runtime165_begin(')
    disassembly = (selected / 'check01/objdump.txt').read_text()
    match = re.search(r'^\w+ <native_session165>:\n(.*?)(?=^\w+ <)', disassembly, re.M | re.S)
    assert match
    prefix = match.group(1).split('<native_boot172>')[0]
    # No index clear/rebuild is hoisted ahead of READY by the compiler.
    assert not re.search(r'\bblx?\b.*<', prefix)
    assert 'nes_runtime165_begin' in match.group(1)
    (a.out / 'native-session-linked.txt').write_text(match.group(0), encoding='utf8')
    packages = [(old/'release01/NES220-SMB3-WAIT-FIX.zip', 'fpga_n220.bi3'),
                (selected/'release01/NES221-SMB3-INDEX.zip', 'fpga_n221.bi3')]
    image_hashes = []
    for path, name in packages:
        with zipfile.ZipFile(path) as z:
            entries = [n for n in z.namelist() if n.endswith('/'+name)]
            assert len(entries) == 1
            image_hashes.append(hashlib.sha256(z.read(entries[0])).hexdigest())
    assert image_hashes[0] == image_hashes[1] == '31908516ec18ea04760328245590eb72c969783e84d82619cf1f5b8be6f592e2'
    check = json.loads((selected / 'check01/result.json').read_bytes())
    assert check['passed'] and check['remaining_margin'] == 1992
    previous = json.loads((ROOT/'analysis/game220-hardware01-verification.json').read_bytes())
    assert previous['budget_fields']['boot_reason'] == '1'
    next_step = ('Investigate physical SNES reset-release -> host bridge admission -> compact ROM/vector '
                 'response -> stage/status observation as one startup boundary, preserving current221 index. '
                 'Include already allocated larger RUN stack and physical image identity in exclusions; '
                 'static RAM margin and identical source do not prove hardware timing. Reuse213/214 evidence; '
                 'do not repeat standalone ROM/FIT tests, blindly retry/extend timeout/revert index, or ask '
                 'for unchanged221/044/video. Resume real first-level scrolling only after startup recovery.')
    result = dict(candidate=221, analysis_checks_passed=True, hardware_passed=False,
        user_report='로딩중에 바로 메뉴로 팅겼어.', raw_inputs=pins, fields=f, budget_fields=b,
        stages=stages, unchanged_startup_sources=sources, packaged_fpga_sha256=image_hashes[1],
        linked_objdump_sha256=sha(selected/'check01/objdump.txt'),
        startup=dict(primary='SNES_READY_TIMEOUT', reason=5, polls=44820, ticks=500,
                     display_interval_ms=elapsed, stage=0, flags=0, signals_before=6, signals_after=6,
                     runtime_begin_reached=False, index_initialization_reached=False,
                     performance_measured=False, reason_branch_distinguished=True),
        recovery=dict(stop=True, base_restored=True, menu_prepared=True, visible_menu_user_confirmed=True),
        comparison220=dict(reason=1, polls=int(previous['budget_fields']['boot_polls']),
                           ticks=int(previous['budget_fields']['boot_ticks']),
                           first=previous['budget_fields']['boot_first_hex'],
                           last=previous['budget_fields']['boot_last_hex']),
        findings=[
            'ROM393216B load/compare and START succeeded; NES observer advanced, SNES client READY did not.',
            'reason5 proves the500tick branch, not service/SPI failure or the60s gameplay deadline.',
            '01000000 means valid status with stage/error/flags all0; not a failed status read.',
            '0606 samples mean RESET unasserted and DONE/MCU_RDY high at entry and exit, not continuous physical waveforms.',
            'No qualified vector/program-read flags or milestone observed. Observation qualification can miss reads; CPU inactivity is unproven.',
            'All252 bin values are zero because runtime never began; failed_transfers0 does not certify the startup bus.',
            'No index initialization/search precedes boot in selected source or linked function. Larger stack reservation already occurs before boot;1992B static margin is not measured high-water.',
            '213 had the same visible stage0/flags0 signature without exact reason. Same root cause is not proven.',
            '220/221 packaged FPGA bytes and startup source are identical; boardID74 alone does not certify installed image bytes.'],
        next=next_step, root_cause_proven=False, fix_complete=False, new_firmware=False, new_fit=False,
        source_sha256=sha(Path(__file__)))
    encoded = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    (a.out/'inputs.json').write_text(json.dumps(pins, indent=2)+'\n', encoding='utf8')
    (a.out/'analysis.json').write_text(encoded, encoding='utf8')
    (ROOT/'analysis/game221-hardware01-verification.json').write_text(encoded, encoding='utf8')
    (a.out/'progress.json').write_text(json.dumps(dict(status='hardware_ready_timeout_before_runtime',
        next=next_step, fixed=False, fps60=False), indent=2)+'\n', encoding='utf8')
    print(json.dumps(result['startup']))


if __name__ == '__main__':
    main()
