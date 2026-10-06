# SPDX-License-Identifier: MIT
"""Replay056 actual STM32 binding pin/sample trace in materialized044+054 RTL."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import sys
from nes_spi_boot import RTL, integrated_boundary, h1_materialize, run, sha, put
from nes_mcu_loader import source

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--host-run', type=Path, required=True)
    p.add_argument('--questa-bin', type=Path, required=True)
    a = p.parse_args()
    if not re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)', os.environ.get('SALT_LICENSE_SERVER', '')):
        p.error('Use the existing authorized FLOAT wrapper')
    host = a.host_run.resolve()
    result = json.loads((host / 'result.json').read_text())
    assert result['host_model_pass'] and result['candidate'] == 'NES-MCU-LOADER-056'
    assert (host / 'nes_h1_stm32.c').read_text() == source()
    for n, digest in result['files'].items():
        assert sha(host / n) == digest, n
    assert sha(host / 'waveform.txt') == result['waveform_sha256']
    for n in ['nes_rom_spi.c', 'nes_rom_spi.h', 'nes_mcu_loader.h']:
        assert sha(host / n) == sha(ROOT / 'src/nes/firmware' / n), n
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), out / 'executed-driver.py')
    files = []
    for n in RTL + ['nes_packet_queue_ram', 'nes_packet_cdc_ram', 'nes_host_stage', 'nes_h1_pattern_producer']:
        shutil.copyfile(ROOT / 'src/nes' / (n + '.sv'), out / (n + '.sv'))
        files.append(n + '.sv')
    h1_materialize(out)
    files += [n + '.sv' for n in ['nes_snes_frontend', 'nes_transport', 'nes_h1_pattern']]
    put(out / 'nes_h1_spi_boot.sv', integrated_boundary())
    files += ['nes_h1_spi_boot.sv', 'rom_boot_model.sv']
    shutil.copyfile(ROOT / 'tests/nes-functional/rom_boot_model.sv', out / 'rom_boot_model.sv')
    run([sys.executable, '-B', ROOT / 'tools/build_nes_h1_board.py', '--out', out / 'h1'], out, 'fixture')
    for n in ['h1-pattern.hex', 'h1-program.hex']:
        shutil.copyfile(out / 'h1/build' / n, out / n)
    shutil.copyfile(host / 'waveform.txt', out / 'waveform.txt')
    # The source fails its second SD pass after256 acknowledged bytes.
    expected = (host / 'banks32/mmc3.nes').read_bytes()
    import hashlib
    assert hashlib.sha256(expected).hexdigest() == result['fixtures']['banks32']
    put(out / 'expected_prg.hex', ''.join(f'{b:02x}\n' for b in expected[16:272]))
    tb = (ROOT / 'tests/nes-functional/rom_spi_wave_tb.sv').read_text()
    tb = tb.replace('module rom_spi_wave_tb;', 'module mcu_loader_wave_tb;\n reg [7:0] expected[0:255];')
    tb = tb.replace('#500;locked=1;', '$readmemh("expected_prg.hex",expected);\n  #500;locked=1;')
    # slow_end restores the original SCK output latch (HIGH in this test).
    # A new independent mode0 transaction must establish its own idle clock.
    assert tb.count('SPI_SS=0;#2000;\n  for') == 1
    tb = tb.replace('SPI_SS=0;#2000;\n  for', 'SPI_SCK=0;#2000;SPI_SS=0;#2000;\n  for')
    old = 'if(memory.writes!=64||loaded_bytes!=0||!spi_fault||spi_error!=2||nes_run_enable)'
    assert tb.count(old) == 1
    tb = tb.replace(old, 'if(memory.writes!=256||loaded_bytes!=0||spi_fault||boot_fault||loaded||nes_run_enable)')
    old = "for(integer i=0;i<64;i++)if(memory.prg[i]!==((i^8'ha5)&255))"
    assert tb.count(old) == 1
    tb = tb.replace(old, 'for(integer i=0;i<256;i++)if(memory.prg[i]!==expected[i])')
    tb = tb.replace('PASS SPI MCU WAVE', 'PASS STM32 LOADER WAVE')
    tb = tb.replace('pin_bytes=64 legacy_queries=4', 'pin_bytes=256 legacy_queries=6 sd_failure_stop=1')
    # No RUN may occur even transiently, including before the final check.
    tb = tb.replace('integer samples=0', 'always @(posedge nes_clk) if(nes_run_enable)$fatal(1,"Unexpected RUN");\n integer samples=0')
    put(out / 'mcu_loader_wave_tb.sv', tb)
    files.append('mcu_loader_wave_tb.sv')
    for tool, args in [('vlib', ['work']), ('vlog', ['-sv', *files]),
                       ('vsim', ['-c', 'mcu_loader_wave_tb', '-do', 'onerror {quit -code 1}; run -all; quit -f'])]:
        log = run([a.questa_bin / (tool + '.exe'), *args], out, tool)
        if re.search(r'\*\* (?:Fatal|Error)(?:\s|:)', log):
            raise RuntimeError('Inspect ' + tool + '.log')
    marker = re.search(r'PASS STM32 LOADER WAVE[^\r\n]*', log)
    if not marker:
        raise RuntimeError('Missing completion marker')
    result = dict(candidate='NES-MCU-LOADER-056', rtl_replay=True, marker=marker[0],
                  host_result_sha256=sha(host / 'result.json'), waveform_sha256=sha(out / 'waveform.txt'),
                  files={n: sha(out / n) for n in files},
                  driver_sha256=sha(Path(__file__)), actual_stm32_execution=False)
    put(out / 'result.json', json.dumps(result, indent=2) + '\n')
    print(marker[0])


if __name__ == '__main__':
    main()
