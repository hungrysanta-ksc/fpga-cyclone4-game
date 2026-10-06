# SPDX-License-Identifier: MIT
"""055: verify a frozen private053 export, load through054 SPI, run actual core.

The private source export is required; this does not vendor upstream HDL or claim
that a clean public clone contains the full core. Production RTL is unchanged.
"""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess
from nes_functional import VHDL, SV
from nes_ncr1_live import sha, put, verify_case

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = 'NES-R1-SPI-LIVE-055'
BASELINE_RESULT = 'result.json'

def replace_once(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)

def prepare(baseline, out):
    meta = json.loads((baseline / BASELINE_RESULT).read_text())
    assert meta['candidate'] == 'NES-R1-ROM-BOOT-053' and meta['passed']
    for n, h in meta['sources'].items():
        assert sha(baseline / n) == h, n
        dest = out / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(baseline / n, dest)
    for n in ('nes_rom_loader.sv', 'nes_rom_boot.sv', 'nes_rom_physical.sv'):
        assert sha(out / n) == sha(ROOT / 'src/nes' / n), n
    assert sha(out / 'rom_backend_model.sv') == sha(ROOT / 'tests/nes-functional/rom_boot_model.sv')
    for n in ('nes_rom_spi.sv', 'nes_spi_boot.sv'):
        shutil.copy2(ROOT / 'src/nes' / n, out / n)
    s = (out / 'ncr1_live_tb.sv').read_text()
    s = replace_once(s, 'reg load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;reg [7:0] load_data=0;',
                     (ROOT / 'tests/nes-functional/spi_live_load.svh').read_text())
    s = replace_once(s, 'nes_rom_boot physical(', 'nes_spi_boot physical(')
    a = s.index('.load_begin(load_begin),')
    b = s.index('.load_ready(load_ready),', a)
    s = s[:a] + '.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),\n.spi_miso(spi_miso),.spi_selected(spi_selected),.spi_fault(spi_fault),.spi_error(spi_error),\n' + s[b:]
    a = s.index(' always @(posedge mem_clk)if(!boot_reset && boot_fault)')
    b = s.index(' integer physical_requests=0,', a)
    s = s[:a] + s[b:]
    # Keep all free-running clocks and per-request/core deadline checks intact.
    # Separate bounded SPI loading time from the original150ms execution budget.
    s = replace_once(s, 'initial begin #60000000;test_arm=1;end',
                     'initial begin wait(run_enable);#60000000;test_arm=1;end')
    s = replace_once(s, 'initial begin repeat(15)begin #10000000;',
                     'initial begin wait(run_enable);repeat(15)begin #10000000;')
    s = replace_once(s, '\nendmodule', '\n initial begin #1000000000;if(!run_enable)$fatal(1,"SPI load watchdog");end\nendmodule')
    assert not re.search(r'memory\.(?:prg|chr)\[[^\]]+\]\s*=(?!=)', s)
    put(out / 'ncr1_live_tb.sv', s)
    names = [*meta['sources'], 'nes_rom_spi.sv', 'nes_spi_boot.sv']
    return {n: sha(out / n) for n in names}

def compare_case(out, baseline, case):
    result = verify_case(out, case)
    c, old = out / case, baseline / case
    offsets = []
    for i in range(1, 5):
        p, q = (c / f'packet-{i}.bin').read_bytes(), (old / f'packet-{i}.bin').read_bytes()
        assert p[:12] + p[16:] == q[:12] + q[16:]
        assert (c / f'frame-{i}.hex').read_bytes() == (old / f'frame-{i}.hex').read_bytes()
        offsets.append(int.from_bytes(p[12:16], 'little') - int.from_bytes(q[12:16], 'little'))
    assert len(set(offsets)) == 1, offsets
    rows = lambda p: [s.split() for s in p.read_text().splitlines() if not s.startswith('B ')]
    before, after = rows(old / 'live.tsv'), rows(c / 'live.tsv')
    assert len(before) == len(after)
    for p, q in zip(before, after):
        j = 4 if p[0] == 'E' else 2
        assert p[:j] + p[j+1:] == q[:j] + q[j+1:] and int(q[j]) - int(p[j]) == offsets[0]
    log = (c / 'simulation.log').read_text()
    total = 98304 if case == 'banks32' else 81920
    assert f'SPI BOOT bytes={total} pin_writes={total} run=1' in log
    physical = re.search(r'PHYSICAL responses=(\d+) latency=(\d+)..(\d+)', log)
    requests = int(re.search(r'ROM SERVICE requests=(\d+)', log)[1])
    assert tuple(map(int, physical.group(2, 3))) == (4, 4)
    assert requests - int(physical[1]) in (0, 1)
    result.update(pin_loaded_bytes=total, tick_offsets_vs053=offsets,
                  rom_requests=requests, rom_responses=int(physical[1]), read_latency_clocks=4)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--questa-bin', type=Path, required=True)
    a = p.parse_args()
    assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)', os.environ.get('SALT_LICENSE_SERVER', ''))
    out, baseline = a.out.resolve(), a.baseline.resolve()
    assert str(out).isascii() and not out.exists()
    out.mkdir()
    meta = dict(candidate=CANDIDATE, passed=False, sources=prepare(baseline, out), cases=[],
                baseline_result_sha256=sha(baseline / BASELINE_RESULT),
                driver_sha256=sha(Path(__file__)), stimulus_sha256=sha(ROOT / 'tests/nes-functional/spi_live_load.svh'),
                scope='Full digital SPI -> pin-written PSRAM -> actual core. Accelerated SPI60ns halves; no STM32/board clocks/consumer or physical signoff.')
    def save(): put(out / 'result.json', json.dumps(meta, indent=2) + '\n')
    def run(tool, args, folder, label, timeout=7200):
        with (folder / label).open('wb') as f:
            cp = subprocess.run([str(a.questa_bin / (tool + '.exe')), *args], cwd=folder,
                                stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
        log = (folder / label).read_text(errors='replace')
        assert cp.returncode == 0 and not re.search(r'\*\* (?:Fatal|Error):', log), str(folder / label)
    save()
    run('vlib', ['work'], out, 'vlib.log')
    for i, n in enumerate(VHDL): run('vcom', ['-2008', n], out, f'vcom-{i:02}.log')
    extra = [n for n in meta['sources'] if n.endswith(('.sv', '.v')) and n not in SV and n != 'ncr1_live_tb.sv']
    run('vlog', ['-sv', '-mfcu', *SV, *extra, 'ncr1_live_tb.sv'], out, 'vlog.log')
    for case in ('banks32', 'fine_x'):
        c = out / case
        c.mkdir()
        for n in ('prg.hex', 'chr.hex', 'manifest.json'):
            shutil.copy2(baseline / case / n, c / n)
        put(c / 'modelsim.ini', '[Library]\nwork = ' + (out / 'work').as_posix() + '\nothers = ' + (a.questa_bin.parent / 'modelsim.ini').as_posix() + '\n')
        print('RUN SPI actual-core ' + case, flush=True)
        run('vsim', ['-c', '-ini', 'modelsim.ini', 'work.ncr1_live_tb', '+CHR32=' + str(int(case == 'banks32')),
                     '-do', 'onerror {quit -code 1}; run -all; quit -f'], c, 'simulation.log')
        meta['cases'].append(compare_case(out, baseline, case)); save()
        print('PASS SPI actual-core ' + case, flush=True)
    meta['passed'] = True; save()
    print('PASS SPI LIVE frames=8 pixels=491520', flush=True)

if __name__ == '__main__': main()
