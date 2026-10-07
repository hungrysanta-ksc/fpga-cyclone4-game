# SPDX-License-Identifier: MIT
"""Verify private078 snapshots and their public source pins, without reruns."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    a = p.parse_args()
    meta = json.loads((ROOT/'analysis/report-session078-verification.json').read_bytes())
    assert sha(a.evidence/'manifest.json') == meta['manifest_sha256']
    files = json.loads((a.evidence/'manifest.json').read_bytes())['files']
    assert len(files) == meta['files']
    for n, h in files.items():
        assert sha(a.evidence/n) == h, n
    for n, h in meta['public_sources'].items():
        assert sha(ROOT/n) == h, n
    for directory, mode in [('run-05','normal'),('no-end-02','no-end'),('no-readback-02','no-readback')]:
        base = a.evidence/'tests'/directory
        result = json.loads((base/'result.json').read_bytes())
        assert result['mode'] == mode and result['physical'] is False
        assert result['checks'] == (116 if mode == 'normal' else None)
        assert result['exit'] == (0 if mode == 'normal' else 3)
        for n, h in result['executed_files'].items():
            assert sha(base/n) == h, (directory,n)
        assert sha(base/'host.c') == meta['public_sources']['tests/nes-functional/report_session078_host.c']
        assert sha(base/'executed-driver.py') == meta['public_sources']['tools/test_nes_report_session078.py']
    print('PASS078 frozen snapshots, normal116, causal2, exact executed/public sources; no physical result')

if __name__ == '__main__':
    main()
