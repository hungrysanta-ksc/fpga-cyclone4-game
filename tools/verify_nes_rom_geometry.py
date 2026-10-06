# SPDX-License-Identifier: MIT
"""Audit057 immutable execution evidence; full-core baseline is private055."""
from pathlib import Path
import argparse
import json
import re
import tempfile
from nes_rom_geometry import ROOT, FILES, materialize
from nes_spi_boot import sha
from nes_spi_live import compare_case


def audit(evidence, baseline):
    runs = {n: json.loads((evidence / n / 'result.json').read_text()) for n in ['unit', 'live', 'fit', 'mutation']}
    for kind, meta in runs.items():
        folder = evidence / kind
        assert meta['candidate'] == 'NES-ROM-GEOMETRY-057'
        assert meta.get('passed') if kind != 'mutation' else meta['negative_control_verified']
        for name, digest in meta['sources'].items():
            assert sha(folder / name) == digest, (kind, name)
        assert sha(folder / 'executed-driver.py') == meta['driver_sha256']
    with tempfile.TemporaryDirectory(prefix='nes-geometry-audit-') as temp:
        expected = Path(temp);materialize(expected)
        for name in FILES:
            for kind in ['unit', 'live', 'fit']:
                assert sha(expected / name) == sha(evidence / kind / name), (kind, name)
    assert 'checks=14 negative_cases=5' in (evidence / 'unit/vsim.log').read_text()
    assert 'checks=360470 bytes=180224 modes=2 run_rebegin_rejected=2' in (evidence / 'unit/vsim.log').read_text()
    assert runs['mutation']['incorrect_design_passed'] is False
    assert runs['mutation']['expected_failure'] in (evidence / 'mutation/vsim.log').read_text()
    assert sha(evidence / 'mutation/vsim.log') == runs['mutation']['log_sha256']
    assert runs['live']['baseline_result_sha256'] == sha(baseline / 'result.json')
    cases = []
    for case in ['banks32', 'fine_x']:
        verified = compare_case(evidence / 'live', baseline, case)
        offsets = verified.pop('tick_offsets_vs053')
        assert offsets == [0, 0, 0, 0]
        verified['tick_offsets_vs055'] = offsets
        log = (evidence / 'live' / case / 'simulation.log').read_text()
        expected = '1 poisoned_argument=0' if case == 'banks32' else '0 poisoned_argument=1'
        assert 'GEOMETRY accepted=' + expected in log
        old = (baseline / case / 'simulation.log').read_text()
        warnings = lambda s: re.findall(r'^# \*\* Warning:[^\r\n]*', s, re.M)
        assert warnings(log) == warnings(old), case
        cases.append(verified)
    assert sum(c['rom_requests'] for c in cases) == 624788
    assert sum(c['rom_responses'] for c in cases) == 624786
    assert sum(c['bus_bytes'] for c in cases) == 16064
    assert sum(c['fetches'] for c in cases) == 131104
    assert sum(len(c['frames']) for c in cases) == 8
    assert sum(f['pixels'] for c in cases for f in c['frames']) == 491520
    for folder in [evidence / 'unit', evidence / 'live']:
        for log in folder.rglob('*.log'):
            if 'work' not in log.parts:
                assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)', log.read_text(errors='replace')), log
    # Quartus Windows reports can contain a non-UTF8 degree symbol. Preserve
    # the raw report bytes/hashes; only parse the required ASCII resource rows.
    rpt = (evidence / 'fit/output_files/live.fit.rpt').read_text(errors='replace')
    lab = int(re.search(r'Total LABs:  partially or completely used\s*;\s*(\d+)', rpt)[1])
    assert lab == 954
    assert 'Total logic elements : 13,976 / 15,408' in runs['fit']['fit_summary']
    assert 'ext_chr_32k' not in (evidence / 'fit/nes_live_joint.sv').read_text()
    assert 'ext_chr_32k' not in (evidence / 'fit/live.qsf').read_text()
    for manifest in ['source-manifest.json', 'cores/nes/publication-sources.json']:
        for entry in json.loads((ROOT / manifest).read_text())['files']:
            assert sha(ROOT / entry['path']) == entry['sha256'], entry['path']
    return dict(candidate='NES-ROM-GEOMETRY-057', passed=True, cases=cases,
                unit_checks=360484, unit_loader_bytes=180224,
                wrong_argument_latch_rejected=True, LE=13976, LAB=lab, LAB_remaining=963-lab,
                registers=5158, M9K=26, new_fit=True, full_board_fit=False,
                physical_readback=False, hardware_image=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    a = p.parse_args();print(json.dumps(audit(a.evidence, a.baseline), indent=2))
