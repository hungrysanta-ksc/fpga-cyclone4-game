# SPDX-License-Identifier: MIT
"""Expected-failure control: exporting the SPI argument instead of accepted ROM geometry."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
from nes_rom_geometry_checks import unit, CANDIDATE
from nes_spi_boot import run, put, sha
from nes_rom_geometry import replace


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--questa-bin', type=Path, required=True)
    a = p.parse_args()
    assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)', os.environ.get('SALT_LICENSE_SERVER', ''))
    out = a.out.resolve();out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__), out / 'executed-driver.py')
    names = unit(out)
    f = out / 'nes_spi_boot.sv'
    s = replace(f.read_text(), '.rom_chr32(rom_chr32)', '.rom_chr32()')
    s = replace(s, 'endmodule', ' assign rom_chr32=load_chr32; // Deliberately WRONG argument latch.\nendmodule')
    put(f, s)
    run([a.questa_bin / 'vlib.exe', 'work'], out, 'vlib')
    log = run([a.questa_bin / 'vlog.exe', '-sv', *names], out, 'vlog')
    assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)', log)
    log = run([a.questa_bin / 'vsim.exe', '-c', 'rom_geometry_tb', '-do',
               'onerror {quit -code 1}; run -all; quit -f'], out, 'vsim')
    # Questa can return0 on $fatal. Require the specific causal failure and
    # reject a compiler error, unrelated failure or unexpectedly passing DUT.
    expected = '** Fatal: Geometry check3 expected1 got0'
    assert expected in log and 'PASS ROM GEOMETRY unit' not in log
    assert log.count('** Fatal:') == 1 and '** Error:' not in log
    result = dict(candidate=CANDIDATE, negative_control_verified=True,
                  incorrect_design_passed=False, expected_failure=expected,
                  sources={n: sha(out / n) for n in names},
                  log_sha256=sha(out / 'vsim.log'), driver_sha256=sha(Path(__file__)))
    put(out / 'result.json', json.dumps(result, indent=2) + '\n')
    print('PASS geometry mutation rejected at illegal BEGIN; not a DUT functional pass')


if __name__ == '__main__':main()
