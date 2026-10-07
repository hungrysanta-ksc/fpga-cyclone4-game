# SPDX-License-Identifier: MIT
"""Frozen066 audit, requiring explicit private evidence; no new execution."""
from pathlib import Path
import argparse, json
from nes_pair_preflight import digest, decode, verify, RBF_SHA

ROOT = Path(__file__).resolve().parents[1]

def audit(e):
    meta = json.loads((ROOT/'analysis/pair-preflight-verification.json').read_text())
    raw_manifest = (e/'manifest.json').read_bytes()
    assert digest(raw_manifest) == meta['manifest_sha256']
    m = json.loads(raw_manifest)
    assert m['candidate'] == meta['candidate']
    assert len(m['files']) == meta['archived_files']
    for name, expected in m['files'].items():
        path = (e/name).resolve()
        assert path.is_relative_to(e.resolve()) and digest(path.read_bytes()) == expected, name
    pair = verify(e/'pair', meta['pair_manifest_sha256'])
    assert pair == meta['pair'] and not pair['installable']
    actual = (e/'pair/reference/board.rbf').read_bytes()
    legacy = decode((e/'legacy-compressor/fpga_nlv.bi3').read_bytes())
    assert digest(actual) == RBF_SHA and legacy == actual+b'\xff'
    assert 'Assertion failed: produced==rn&&!memcmp(output,raw,rn)' in (e/'programmer.log').read_text()
    assert 'compressed=209943 raw=510856 all_bytes=1' in (e/'programmer-02.log').read_text()
    assert 'compressed=531 raw=66309 all_bytes=1' in (e/'programmer-boundaries.log').read_text()
    assert 'Database format is incompatible' in (e/'asm-01.log').read_text()
    for phase in ['asm', 'cpf']:
        log = (e/'assembly'/(phase+'-066.log')).read_text()
        assert 'successful. 0 errors, 0 warnings' in log and 'SC Standard Edition' in log
    for name, expected in meta['fit_inputs'].items():
        assert digest((e/'assembly'/name).read_bytes()) == expected, name
    db = json.loads((e/'database-inventory.json').read_text())
    assert len(db) == meta['database_files']
    assert digest(json.dumps(sorted([n,h] for n,h in db.items()),separators=(',',':')).encode()) == meta['database_sha256']
    tests = json.loads((e/'tests/result.json').read_text())
    assert tests == dict(tests=18, failures=0, errors=0, skipped=0, physical_sd=False,
                         pair_manifest_sha256=meta['pair_manifest_sha256'])
    plan = json.loads((e/'tests/test_12_candidate_restore_plan/rollback-plan.json').read_text())
    assert plan['read_only'] and not plan['executed'] and len(plan['actions']) == 6
    assert sum(a['action']=='restore' for a in plan['actions']) == 1
    for name in ['nes_diag_runtime.c', 'nes_diag_runtime.h', 'nes_diag_fpga.inc']:
        assert digest((e/'programmer'/name).read_bytes()) == digest((ROOT/'src/nes/firmware'/name).read_bytes())
    for name in ['nes_pair_preflight.py', 'nes_pair_assemble.py', 'verify_nes_pair_preflight.py']:
        assert digest((e/'executed-tools'/name).read_bytes()) == digest((ROOT/'tools'/name).read_bytes())
    print('PASS066 frozen files='+str(len(m['files']))+' tests=18 programmer_all_bytes=510856; no physical SD/install')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    audit(p.parse_args().evidence)
