# SPDX-License-Identifier: MIT
"""Audit055 raw execution and frozen053 reference; does not run a simulator."""
from pathlib import Path
import argparse, json, re
from nes_spi_live import ROOT, CANDIDATE, sha, compare_case

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))

def audit(raw, baseline, fit):
    meta, before, resource = (read(p / 'result.json') for p in (raw, baseline, fit))
    assert meta['candidate'] == CANDIDATE and meta['passed']
    assert meta['baseline_result_sha256'] == sha(baseline / 'result.json')
    assert meta['driver_sha256'] == sha(ROOT / 'tools/nes_spi_live.py')
    assert meta['stimulus_sha256'] == sha(ROOT / 'tests/nes-functional/spi_live_load.svh')
    for folder, result in ((raw, meta), (baseline, before), (fit, resource)):
        for n, h in result['sources'].items(): assert sha(folder / n) == h, (folder.name, n)
    for n, h in before['sources'].items():
        if n != 'ncr1_live_tb.sv': assert meta['sources'][n] == h, n
    # Reuse054 area evidence only because every synthesizable core/module byte
    # is unchanged. The new stimulus is not a new physical fit or STA run.
    shared = []
    for n, h in meta['sources'].items():
        if n in ('ncr1_live_tb.sv', 'rom_backend_model.sv') or not n.endswith(('.sv', '.v', '.vhd')): continue
        assert resource['sources'][n] == h, n
        shared.append(n)
    for n in ('nes_rom_spi', 'nes_spi_boot', 'nes_rom_loader', 'nes_rom_boot', 'nes_rom_physical'):
        assert meta['sources'][n + '.sv'] == sha(ROOT / 'src/nes' / (n + '.sv'))
    model = (raw / 'rom_backend_model.sv').read_text()
    tb = (raw / 'ncr1_live_tb.sv').read_text()
    assert '$readmemh' not in model and not re.search(r'memory\.(?:prg|chr)\[[^\]]+\]\s*=(?!=)', tb)
    cases = [compare_case(raw, baseline, c) for c in ('banks32', 'fine_x')]
    assert cases == meta['cases']
    warnings = {}
    for case in ('banks32', 'fine_x'):
        for n in ('prg.hex', 'chr.hex', 'manifest.json'): assert sha(raw / case / n) == sha(baseline / case / n)
        prior = [s for s in (baseline / case / 'simulation.log').read_text().splitlines() if '** Warning:' in s]
        current = [s for s in (raw / case / 'simulation.log').read_text().splitlines() if '** Warning:' in s]
        assert current == prior, (case, 'new simulation warnings')
        warnings[case] = len(current)
    for path in raw.glob('*.log'):
        assert not re.search(r'\*\* (?:Fatal|Error):', path.read_text(errors='replace')), path.name
    for e in read(ROOT / 'source-manifest.json')['files']: assert sha(ROOT / e['path']) == e['sha256']
    for e in read(ROOT / 'cores/nes/publication-sources.json')['files']: assert sha(ROOT / e['path']) == e['sha256']
    return dict(candidate=CANDIDATE, actual_frames=8, exact_pixels=491520, fetches=131104,
                packet_bytes=16064, pin_bytes={c['case']: c['pin_loaded_bytes'] for c in cases},
                tick_offsets_vs053={c['case']: c['tick_offsets_vs053'] for c in cases},
                ROM_requests=sum(c['rom_requests'] for c in cases), ROM_responses=sum(c['rom_responses'] for c in cases),
                unchanged_synthesis_sources_vs054=len(shared), reused_fit_candidate='NES-R1-SPI-BOOT-054',
                protected_GBC=152, original_NES_sources=334, inherited_warning_messages=warnings, new_fit_run=False,
                hardware_baseline='044 unchanged', new_SD_image=False)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--fit', type=Path, required=True)
    a = p.parse_args()
    result = audit(a.evidence, a.baseline, a.fit)
    published = read(ROOT / 'analysis/spi-live-verification.json')
    for k, v in result.items(): assert published[k] == v, k
    for n, h in published['logs'].items(): assert sha(a.evidence / n) == h, n
    manifest = a.evidence.parent / 'manifest.json'
    assert sha(manifest) == published['evidence_manifest_sha256']
    for e in read(manifest)['files']:
        f = manifest.parent / e['path']
        assert f.stat().st_size == e['bytes'] and sha(f) == e['sha256'], e['path']
    failed = manifest.parent / 'status-expectation-failed/banks32/simulation.log'
    assert sha(failed) == published['failed_status_expectation_log_sha256']
    assert 'Fatal: SPI status count=98304 flags=1' in failed.read_text()
    controls = read(manifest.parent / 'comparator/result.json')
    assert controls == published['comparator_controls'] and controls['passed']
    assert controls['new_RTL_execution'] is False and len(controls['rejected']) == 2
    assert controls['driver_sha256'] == sha(ROOT / 'tools/nes_spi_live_compare_checks.py')
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
