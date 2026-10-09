# SPDX-License-Identifier: MIT
"""Verify immutable release evidence and exact role identities, not hardware safety."""
from pathlib import Path
import argparse
import json
import zipfile
from nes_spi_boot import ROOT, sha
from nes_pair109 import expected, digest

ROLES = {
    '01-TRIAL-SD-ROOT/sd2snes/firmware.stm': 'arm108.stm',
    '01-TRIAL-SD-ROOT/sd2snes/fpga_n86.bi3': 'cf86.packed',
    '01-TRIAL-SD-ROOT/sd2snes/fpga_base.bi3': 'base.packed',
    '01-TRIAL-SD-ROOT/sd2snes/m3nu.bin': 'menu.bin',
    '01-TRIAL-SD-ROOT/sd2snes/nes/fine_x.nes': 'fixture80.nes',
    '01-TRIAL-SD-ROOT/NES VERIFY 094 80.nh1': 'marker0.empty',
    '02-RESTORE044-SD-ROOT/sd2snes/firmware.stm': 'restore044.stm',
    '02-RESTORE044-SD-ROOT/sd2snes/fpga_base.bi3': 'base.packed',
    '02-RESTORE044-SD-ROOT/sd2snes/m3nu.bin': 'menu.bin'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    e = p.parse_args().evidence
    meta = json.loads((ROOT/'analysis/trial111-verification.json').read_bytes())
    assert sha(e/'manifest.json') == meta['manifest_sha256']
    pins = json.loads((e/'manifest.json').read_bytes())['files']
    assert len(pins) == meta['archived_files']
    for n, h in pins.items():
        assert sha(e/n) == h, n
    for n, h in meta['public_sources'].items():
        assert sha(ROOT/n) == h == sha(e/'public-sources'/n), n
    assert sha(e/'release01/executed-release111.py') == meta['public_sources']['tools/release_nes_trial111.py']
    r = json.loads((e/'release01/result.json').read_bytes())
    assert r == meta['release'] and r['members'] == 12 and r['binary_roles'] == 9
    zpath = e/'release01/NES111-80KiB-TRIAL-and-RESTORE044.zip'
    assert sha(zpath) == r['zip_sha256'] and zpath.stat().st_size == r['zip_bytes']
    with zipfile.ZipFile(zpath) as z:
        names = set(ROLES) | {'START-HERE.ko.md', 'decision111.json', 'manifest.json'}
        assert set(z.namelist()) == names and len(z.namelist()) == len(names)
        m = json.loads(z.read('manifest.json'))
        assert set(m['files']) == names - {'manifest.json'}
        for n, v in m['files'].items():
            assert len(z.read(n)) == v['bytes'] and digest(z.read(n)) == v['sha256'], n
        for n, role in ROLES.items():
            v = expected()[role]
            assert digest(z.read(n)) == v['sha256'] and len(z.read(n)) == v['bytes'], role
            assert m['files'][n]['source_role'] == role
        assert z.read('START-HERE.ko.md') == (ROOT/'docs/nes-trial111-instructions.ko.md').read_bytes()
        assert z.read('decision111.json') == (ROOT/'docs/nes-trial111-decision.json').read_bytes()
        d = json.loads(z.read('decision111.json'))
        assert d['authorization_source'] == 'direct_user_message'
        assert d['hardware_trial_approved'] and d['limited_trial_installable']
        assert d['attempts'] == 1 and d['fixture_kib'] == 80
        for key in ['full_nes_installable', 'start_enabled', 'external_io_signoff',
                    'common_cause_8us_proven', 'intentional_fault_injection']:
            assert d[key] is False, key
        assert d['physical_result'] == 'pending'
    assert not r['new_firmware'] and not r['new_fpga']
    print('PASS111: immutable evidence, exact 9 roles/12 members, authorized single trial; hardware result pending')

if __name__ == '__main__':
    main()
