# SPDX-License-Identifier: MIT
"""057 geometry unit/core/fit jobs; private exports required only for core/fit."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import sys
from nes_rom_geometry import ROOT, FILES, materialize, bind_core, replace
from nes_spi_boot import run, put, sha
from nes_spi_live import compare_case
from nes_functional import VHDL, SV

CANDIDATE = 'NES-ROM-GEOMETRY-057'


def copy_baseline(base, out, candidate):
    previous = json.loads((base / 'result.json').read_text())
    assert previous['candidate'] == candidate
    if 'passed' in previous:
        assert previous['passed']
    for name, digest in previous['sources'].items():
        assert sha(base / name) == digest, name
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base / name, target)
    materialize(out)
    return previous


def unit(out):
    materialize(out)
    names = FILES + ['nes_rom_spi.sv', 'nes_rom_physical.sv']
    for n in ['nes_rom_spi.sv', 'nes_rom_physical.sv']:
        shutil.copy2(ROOT / 'src/nes' / n, out / n)
    for n in ['rom_boot_model.sv', 'rom_geometry_loader.sv']:
        shutil.copy2(ROOT / 'tests/nes-functional' / n, out / n)
        names.append(n)
    text = (ROOT / 'tests/nes-functional/rom_spi_tb.sv').read_text()
    text = text[:text.index(' integer i,writes_before;')]
    text = replace(text, 'module rom_spi_tb;', '''module rom_geometry_tb;
 reg spi_done=0;wire loader_done,rom_chr32;
 rom_geometry_loader geometry_loader(.done(loader_done));''')
    text += (ROOT / 'tests/nes-functional/rom_geometry_checks.svh').read_text()
    text += '''
 initial begin wait(spi_done&&loader_done);$display("PASS ROM GEOMETRY unit");$finish;end
 initial begin #50000000;$fatal(1,"Geometry watchdog");end
endmodule
'''
    put(out / 'rom_geometry_tb.sv', text)
    names.append('rom_geometry_tb.sv')
    return names


def live(base, out):
    previous = copy_baseline(base, out, 'NES-R1-SPI-LIVE-055')
    text = (out / 'ncr1_live_tb.sv').read_text()
    text = replace(text, 'reg chr_32k;', 'wire chr_32k;reg fixture_chr32;')
    text = replace(text, 'total=65536+(chr_32k?32768:16384);command(8\'h60,0,{7\'d0,chr_32k});status(0,1);',
                   '''total=65536+(fixture_chr32?32768:16384);command(8'h60,0,{7'd0,fixture_chr32});status(0,1);
  if(chr_32k!==fixture_chr32)$fatal(1,"Accepted geometry mismatch");
  fixture_chr32=~fixture_chr32; // Poison the old independent configuration input.''')
    text = replace(text, '$value$plusargs("CHR32=%d",chr_32k)', '$value$plusargs("CHR32=%d",fixture_chr32)')
    text = replace(text, '$readmemh("chr.hex",chr,0,chr_32k?32767:16383)', '$readmemh("chr.hex",chr,0,fixture_chr32?32767:16383)')
    text = bind_core(text)
    text = replace(text, 'if(!run_enable)$fatal(1,"SPI START handshake");', '''if(!run_enable)$fatal(1,"SPI START handshake");
  if(chr_32k!==(total==98304)||chr_32k===fixture_chr32)$fatal(1,"Independent geometry still drives core");
  $display("GEOMETRY accepted=%0d poisoned_argument=%0d",chr_32k,fixture_chr32);''')
    put(out / 'ncr1_live_tb.sv', text)
    return previous, list(previous['sources'])


def fit(base, out):
    previous = copy_baseline(base, out, 'NES-R1-SPI-BOOT-054')
    text = (out / 'nes_live_joint.sv').read_text()
    text = replace(text, 'input wire  ext_chr_32k,\n', '')
    text = replace(text, 'wire chr_32k=ext_chr_32k;', 'wire chr_32k;')
    put(out / 'nes_live_joint.sv', bind_core(text))
    qsf = (out / 'live.qsf').read_text()
    qsf = replace(qsf, 'set_instance_assignment -name VIRTUAL_PIN ON -to ext_chr_32k\n', '')
    put(out / 'live.qsf', qsf)
    return previous, list(previous['sources'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['unit', 'live', 'fit'], required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--baseline', type=Path)
    p.add_argument('--questa-bin', type=Path)
    p.add_argument('--quartus-bin', type=Path)
    a = p.parse_args()
    if a.mode != 'fit':
        assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)', os.environ.get('SALT_LICENSE_SERVER', ''))
    out = a.out.resolve()
    assert str(out).isascii()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__), out / 'executed-driver.py')
    shutil.copy2(ROOT / 'tools/nes_rom_geometry.py', out / 'geometry-generator.py')
    previous = None
    if a.mode == 'unit':
        names = unit(out)
    else:
        assert a.baseline
        base = a.baseline.resolve()
        previous, names = (live if a.mode == 'live' else fit)(base, out)
    result = dict(candidate=CANDIDATE, mode=a.mode, passed=False,
                  sources={n: sha(out / n) for n in names},
                  driver_sha256=sha(Path(__file__)), generator_sha256=sha(ROOT / 'tools/nes_rom_geometry.py'),
                  hardware_image=False, cases=[])
    if previous:
        result['baseline_result_sha256'] = sha(base / 'result.json')
    def save():put(out / 'result.json', json.dumps(result, indent=2) + '\n')
    save()
    def simulate(tool, args, folder, label, timeout=7200):
        text = run([a.questa_bin / (tool + '.exe'), *args], folder, label, timeout)
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)', text), str(folder / label)
        return text
    if a.mode == 'fit':
        for phase in ['map', 'fit']:
            run([a.quartus_bin / ('quartus_' + phase + '.exe'), 'live'], out, phase, 3600)
        result['fit_summary'] = (out / 'output_files/live.fit.summary').read_text()
        print(result['fit_summary'])
    else:
        simulate('vlib', ['work'], out, 'vlib')
        if a.mode == 'unit':
            simulate('vlog', ['-sv', *names], out, 'vlog')
            log = simulate('vsim', ['-c', 'rom_geometry_tb', '-do', 'onerror {quit -code 1}; run -all; quit -f'], out, 'vsim')
            assert 'PASS ROM GEOMETRY unit' in log
            result['markers'] = re.findall(r'PASS [^\r\n]+', log)
        else:
            for i, n in enumerate(VHDL):simulate('vcom', ['-2008', n], out, f'vcom-{i:02}')
            extra = [n for n in names if n.endswith(('.sv', '.v')) and n not in SV and n != 'ncr1_live_tb.sv']
            simulate('vlog', ['-sv', '-mfcu', *SV, *extra, 'ncr1_live_tb.sv'], out, 'vlog')
            for case in ['banks32', 'fine_x']:
                c = out / case;c.mkdir()
                for n in ['prg.hex', 'chr.hex', 'manifest.json']:shutil.copy2(base / case / n, c / n)
                put(c / 'modelsim.ini', '[Library]\nwork = ' + (out / 'work').as_posix() + '\nothers = ' + (a.questa_bin.parent / 'modelsim.ini').as_posix() + '\n')
                print('RUN GEOMETRY ' + case, flush=True)
                log = simulate('vsim', ['-c', '-ini', 'modelsim.ini', 'work.ncr1_live_tb', '+CHR32=' + str(int(case == 'banks32')),
                                       '-do', 'onerror {quit -code 1}; run -all; quit -f'], c, 'simulation')
                verified = compare_case(out, base, case)
                offsets = verified.pop('tick_offsets_vs053')
                assert offsets == [0, 0, 0, 0], offsets
                verified['tick_offsets_vs055'] = offsets
                assert 'GEOMETRY accepted=' in log
                result['cases'].append(verified);save()
                print('PASS GEOMETRY ' + case, flush=True)
    result['passed'] = True;save();print('PASS ROM GEOMETRY ' + a.mode, flush=True)


if __name__ == '__main__':main()
