# SPDX-License-Identifier: MIT
"""Verify preserved partial results without reclassifying failed game runs."""
from pathlib import Path
import argparse, json
from nes_game147 import ROOT, sha

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    a = p.parse_args()
    meta = json.loads((ROOT/'analysis/game147-verification.json').read_bytes())
    evidence = a.baseline/'nes-game147/evidence'
    assert sha(evidence/'manifest.json') == meta['manifest_sha256']
    files = json.loads((evidence/'manifest.json').read_bytes())['files']
    assert len(files) == meta['file_count']
    for name, digest in files.items():
        assert sha(evidence/name) == digest, name
    for name, digest in meta['public_sources'].items():
        assert sha(ROOT/name) == digest, name
    for name in ['unit03', 'unit04', 'prefetch01']:
        assert json.loads((evidence/name/'result.json').read_bytes())['passed']
    for run in meta['core_runs']:
        result = json.loads((evidence/run['run']/'result.json').read_bytes())
        log = (evidence/run['run']/'simulation.log').read_text()
        assert not result['passed'] and not run['passed']
        assert sha(evidence/run['run']/'simulation.log') == run['log_sha256']
        assert 'PASS GAME147' not in log and '** Fatal: PPU ROM byte mismatch' in log
        assert f"PPU147 frame={run['failure_frame']} line=193 dot={run['dot']} valid=0" in log
        assert f"addr={run['address']}" in log
    core = json.loads((evidence/'core03/result.json').read_bytes())
    reproduction = json.loads((evidence/'reproduction-check.json').read_bytes())
    assert core['sources'] == reproduction['sources']
    for name in ['nes_rom_service.sv', 'nes_rom_physical.sv']:
        assert meta['prefetch_boundary']['sources'][name] == core['sources'][name]
    assert meta['status'] == 'PARTIAL_NOT_INSTALLABLE'
    assert not meta['physical_test'] and not meta['sd_package']
    print('PASS147 evidence/source integrity; path and first-boundary PASS; whole game FAIL retained; no SD package')

if __name__ == '__main__':
    main()
