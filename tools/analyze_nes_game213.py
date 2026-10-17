# SPDX-License-Identifier: MIT
"""Preserve hardware213 startup failure; do not treat empty bins as performance."""
from pathlib import Path
import argparse, hashlib, json, re, shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def fields(p):
    lines = [x.strip() for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
    result = dict(x.split('=', 1) for x in lines)
    assert len(result) == len(lines)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    raw = a.out / 'raw'; raw.mkdir()
    pins = {}
    for kind in ['progress', 'game-last', 'budget']:
        name = f'nes-{kind}-213.txt'
        shutil.copyfile(a.inputs / name, raw / name)
        assert sha(a.inputs / name) == sha(raw / name)
        pins[name] = dict(bytes=(raw / name).stat().st_size, sha256=sha(raw / name))
    f = fields(raw / 'nes-game-last-213.txt')
    b = fields(raw / 'nes-budget-213.txt')
    stages = [dict(re.findall(r'(\w+)=(\S+)', x)) for x in
              (raw / 'nes-progress-213.txt').read_text().splitlines() if x.strip()]
    assert [int(x['seq']) for x in stages] == list(range(100))
    by = {x['stage']: x for x in stages}
    assert f['candidate'] == 'NES-GAME-213'
    assert f['loaded_bytes'] == f['compared_bytes'] == '393216'
    for k in ['verified', 'end_accepted', 'start_sent', 'stop_ok', 'base_restored', 'safe_to_reload', 'screen_status_valid']:
        assert f[k] == '1', k
    for k in ['verify_error', 'run_rom_error', 'run_stop_error', 'run_passed', 'screen_stage',
              'screen_flags', 'screen_frames', 'native_frames', 'native_transactions',
              'native_wire_bytes', 'trace_begins', 'trace_ends', 'trace_commits',
              'plan_sent', 'sink_window_sent', 'sink_window_retired']:
        assert f[k] == '0', k
    assert f['run_error'] == f['run_first_error'] == '6' and f['native_result'] == '2'
    assert f['menu_state'] == 'PREPARED_RESET_HELD'
    elapsed = int(by['DISPLAY_STOPPED']['elapsed_ms']) - int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert elapsed == 5020
    assert b['budget_schema'] == '213' and b['open'] == b['failed_transfers'] == '0'
    for i in range(12):
        values = b[f'b{i:02}'].split(',')
        assert len(values) == 19 and all(int(x, 16) == 0 for x in values)
    src = BASE / 'probes/nes-runtime213/arm01/src'
    boot = (src / 'nes_boot172.inc').read_text()
    runtime = (src / 'nes_runtime_board165.inc').read_text()
    assert '>=500u' in boot and 'screen_stage==3' in boot and 'first_error=6' in boot
    assert runtime.index('if(!native_boot172(io))') < runtime.index('nes_runtime165_begin(')
    assert sha(src / 'nes_boot172.inc') == sha(BASE / 'probes/nes-budget210/arm03/src/nes_boot172.inc')
    old = bytes.fromhex((BASE / 'probes/nes-board207/mapfit02/sink-program.hex').read_text())
    new = bytes.fromhex((BASE / 'probes/nes-runtime213/asm01/sink-program.hex').read_text())
    # First software milestone is before the changed copy length/body.
    milestone = bytes.fromhex('a9 01 8d 00 70')
    end = old.index(milestone) + len(milestone)
    assert new[:end] == old[:end]
    assert old[0xffc:0xffe] == new[0xffc:0xffe] == bytes.fromhex('00 80')
    paths = [src / 'nes_boot172.inc', src / 'nes_runtime_board165.inc',
             BASE / 'probes/nes-board207/mapfit02/nes_screen_status151.sv',
             BASE / 'probes/nes-board207/mapfit02/nes_sink_bus165.sv',
             BASE / 'probes/nes-board207/mapfit02/fxpak_nes_screen137_top.sv']
    result = dict(candidate=213, analysis_checks_passed=True, hardware_passed=False,
        user_report='아에 실행에 실패했어. 확인해봐', raw_inputs=pins, fields=f,
        stages=stages, budget=b, source_pins={x.relative_to(BASE).as_posix(): sha(x) for x in paths},
        startup=dict(elapsed_ms=elapsed, loaded_and_compared_bytes=393216,
            primary='SNES_READY_NOT_REACHED', first_error=6, timeout_ticks=500,
            timeout_consistent=True, exact_last_poll_reason_logged=False,
            reset_vector_and_program_read_flags=0, first_stage=0,
            same_initial_boot_bytes=end, reset_vector_hex='0080',
            runtime_begin_reached=False, fps_measurement_valid=False),
        recovery=dict(stop=True, base_restored=True, menu_prepared=True, visible_menu_user_confirmed=False),
        interpretation=[
            'Failure is before resident begin/first transfer; zero budget is unstarted, not free work or transfer failure count proof.',
            'No qualified reset-vector/program reads or software milestones observed. Investigate SNES reset handoff, bus admission/ROM response and status qualification together.',
            'Status is retained across STOP; stage0 is not merely renderer reset on exit. Hardware bus waveforms and full firmware/FPGA identity were not logged.',
            'Unchanged reset vector and bytes through stage1 weaken a new body-initialization-only explanation, but do not prove electrical boot.',
            'Standalone ROM Mesen + separate RTL queue tests omitted the physical reset/vector/ROM startup join. ROM atom equality does not close that gap.',
            '5020ms matches ready timeout; service/SPI failures share error6, so exact final branch is not distinguishable from current log.'],
        next='Close minimal startup boundary: actual packaged compact ROM/reset vector + board ROM/status admission + production reset release/READY, compared with working210. If local failure remains unreproduced, next paired fix must retain first startup cause/activity without unbounded retries. No blind timeout increase, cache rollback, new FIT, or repeated unchanged213/044 test.',
        new_package=False, new_fit=False, public_source_sha256=sha(Path(__file__)))
    out = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    (a.out / 'analysis.json').write_text(out, encoding='utf8')
    (ROOT / 'analysis/game213-hardware01-verification.json').write_text(out, encoding='utf8')
    (a.out / 'progress.json').write_text(json.dumps(dict(status='hardware_failed_before_first_transfer',
        next=result['next'], fixed=False), ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result['startup']))

if __name__ == '__main__':
    main()
