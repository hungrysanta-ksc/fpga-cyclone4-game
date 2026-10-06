# SPDX-License-Identifier: MIT
"""056: append load-only SD/GPIO binding to the unchanged materialized044."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from nes_h1_sampling import source as source044, session as session044
from build_nes_video_workloads import build

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / 'src/nes/firmware'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source():
    base = source044()
    result = base + '\n' + (FW / 'nes_mcu_loader.inc').read_text(encoding='utf-8')
    assert result[:len(base)] == base
    return result


def materialize(out):
    for name in ['nes_rom_spi.c', 'nes_rom_spi.h', 'nes_mcu_loader.h',
                 'nes_h1_stm32.h', 'nes_h1_session.h']:
        shutil.copyfile(FW / name, out / name)
    (out / 'nes_h1_stm32.c').write_text(source(), encoding='utf-8', newline='\n')
    (out / 'nes_h1_session.c').write_text(session044(), encoding='utf-8', newline='\n')


def run(command, out, label):
    with (out / (label + '.log')).open('wb') as log:
        result = subprocess.run([str(x) for x in command], cwd=out,
                                stdout=log, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode:
        raise RuntimeError(f'{label} failed ({result.returncode}); inspect its raw log')
    return (out / (label + '.log')).read_text(errors='replace')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--gcc', type=Path)
    p.add_argument('--upstream', type=Path)
    a = p.parse_args()
    out = a.out.resolve()
    if a.upstream:
        if out.exists():
            p.error('Fresh output required')
        subprocess.run([sys.executable, '-B', '-X', 'utf8', ROOT / 'tools/nes_h1_sampling.py',
                        '--out', out, '--upstream', a.upstream.resolve()], check=True)
        materialize(out / 'src')
        mk = out / 'src/Makefile'
        text = mk.read_text()
        needle = 'SRC += nes_h1_session.c nes_h1_stm32.c'
        assert text.count(needle) == 1
        text = text.replace(needle, needle + ' nes_rom_spi.c')
        needle = 'LDFLAGS += -Wl,--gc-sections'
        assert text.count(needle) == 1
        # Retain the uncalled diagnostic entry for a real full-link check.
        # This is not a menu hook and does not make an installable candidate.
        text = text.replace(needle, needle + '\nLDFLAGS += -Wl,--undefined=nes_mcu_load_probe')
        mk.write_text(text, newline='\n')
        names = ['nes_h1_stm32.c', 'nes_h1_session.c', 'nes_rom_spi.c',
                 'nes_rom_spi.h', 'nes_mcu_loader.h', 'Makefile', 'main.c', 'filetypes.c']
        (out / 'mcu-loader-preparation.json').write_text(json.dumps(dict(
            candidate='NES-MCU-LOADER-056', menu_entry=False, start_enabled=False,
            files={n: sha(out / 'src' / n) for n in names}), indent=2) + '\n')
        # No call site is added. Board gates must be met before menu integration.
        print('Prepared load-only056 binding; existing044 menu hook unchanged')
        return
    if not a.gcc:
        p.error('--gcc required for host regression')
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), out / 'executed-driver.py')
    materialize(out)
    for name in ['mcu_loader_platform.h', 'mcu_loader_host.c']:
        shutil.copyfile(ROOT / 'tests/nes-functional' / name, out / name)
    for name in ['config', 'bits', 'timer', 'snes', 'fpga', 'fpga_spi', 'fileops', 'uart']:
        (out / (name + '.h')).write_text('#include "mcu_loader_platform.h"\n')
    fixtures = {c: build(out / c, c) for c in ['fine_x', 'banks32']}
    run([a.gcc, '-std=c11', '-D__USE_MINGW_ANSI_STDIO=1', '-Wall', '-Wextra', '-Werror',
         '-O2', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
         'nes_rom_spi.c', 'nes_h1_stm32.c', 'nes_h1_session.c', 'mcu_loader_host.c',
         '-o', 'loader.exe'], out, 'host_compile')
    log = run([out / 'loader.exe', out / 'fine_x/mmc3.nes', out / 'banks32/mmc3.nes',
               out / 'waveform.txt'], out, 'host')
    marker = 'PASS MCU LOADER lifecycle=26 header_rejections=18 no_start=1 no_sd_writes=1'
    if marker not in log:
        raise RuntimeError('Missing host completion marker')
    paths = sorted(p for p in out.iterdir() if p.suffix in ['.h', '.c', '.log'])
    result = dict(candidate='NES-MCU-LOADER-056', host_model_pass=True,
                  marker=marker, actual_stm32_execution=False, rtl_replay=False,
                  materialized044_prefix_sha256=hashlib.sha256(source044().encode()).hexdigest(),
                  fixtures={c: m['sha256'] for c, m in fixtures.items()},
                  files={p.name: sha(p) for p in paths}, waveform_sha256=sha(out / 'waveform.txt'),
                  driver_sha256=sha(Path(__file__)))
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(marker)


if __name__ == '__main__':
    main()
