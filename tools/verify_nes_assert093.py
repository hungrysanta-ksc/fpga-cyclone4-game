# SPDX-License-Identifier: MIT
"""Read-only frozen093 integrity and three-corner assertion-graph replay."""
from pathlib import Path
import argparse, json
from nes_clock_assert093 import analyze, digest
from run_nes_assert093 import CORNERS
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(); p.add_argument('--evidence', type=Path, required=True)
    e = p.parse_args().evidence.resolve()
    meta = json.loads((ROOT/'analysis/assertion093-verification.json').read_bytes())
    assert digest(e/'manifest.json') == meta['manifest_sha256']
    inventory = json.loads((e/'manifest.json').read_bytes())['files']
    assert len(inventory) == meta['archived_files']
    for name, checksum in inventory.items():
        path = (e/name).resolve(); assert path.is_relative_to(e) and digest(path) == checksum, name
    for name, checksum in meta['public_sources'].items():
        assert digest(ROOT/name) == checksum, name
    normal = e/'normal03'; paths = 0
    for vo, sdf in CORNERS:
        actual = analyze(normal/'simulation/modelsim'/('board_'+vo+'.vo'),
                         normal/'simulation/modelsim'/('board_'+sdf+'.sdo'))
        actual['corner'] = vo
        expected = json.loads((normal/('assert-'+vo+'.json')).read_bytes())
        assert actual == expected; paths += len(actual['paths'])
    result = json.loads((normal/'result.json').read_bytes())
    assert paths == result['path_count'] == 264 and result['maximum_ps'] == 23699
    tests = json.loads((e/'causal01/result.json').read_bytes())
    assert len(tests['controls']) == 4 and all(x['expected_failure'] for x in tests['controls'])
    source = json.loads((e/'pinned-fit086-result.json').read_bytes())
    assert source['identity_hex'] == '86' and digest(e/'pinned-fit086-result.json') == result['fit_result_sha256']
    old = json.loads((ROOT/'analysis/clock086-verification.json').read_bytes())
    for name, checksum in old['public_sources'].items():
        assert digest(ROOT/name) == checksum, name
    assert meta['reference_activity_observed092'] and not meta['external_io_signoff']
    assert not meta['sdf_simulation_run'] and not meta['both_clock_halt_safe'] and not meta['installable']
    print('PASS093: frozen evidence, sameCF86 fit, three corners/264 paths max23.699ns, four causal controls; board signoff=false')


if __name__ == '__main__':
    main()
