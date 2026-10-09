# SPDX-License-Identifier: MIT
"""Package the explicitly authorized single 80KiB hardware trial; no SD writes."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile
from nes_pair109 import verify
from nes_spi_boot import ROOT
from stage_nes_trial110 import FILES, PAIR

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pair', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Use a new output directory; never overwrite a release')
    decision_bytes = (ROOT/'docs/nes-trial111-decision.json').read_bytes()
    decision = json.loads(decision_bytes)
    assert decision['authorization_source'] == 'direct_user_message'
    assert decision['selection'] == 'limited_normal80_single_trial'
    assert decision['limited_trial_installable'] and decision['hardware_trial_approved']
    assert decision['attempts'] == 1 and decision['fixture_kib'] == 80
    assert not any(decision[k] for k in ('start_enabled', 'full_nes_installable',
               'external_io_signoff', 'common_cause_8us_proven', 'intentional_fault_injection'))
    assert decision['pair_manifest_sha256'] == PAIR
    assert verify(a.pair, PAIR)['pair_identity_pass']
    roles = {n.replace('review-only/trial/', '01-TRIAL-SD-ROOT/').replace(
             'review-only/restore/', '02-RESTORE044-SD-ROOT/'): role
             for n, role in FILES.items()}
    blobs = {n: (a.pair/'files'/role).read_bytes() for n, role in roles.items()}
    blobs['START-HERE.ko.md'] = (ROOT/'docs/nes-trial111-instructions.ko.md').read_bytes()
    blobs['decision111.json'] = decision_bytes
    manifest = dict(candidate='NES-LIMITED-TRIAL-111',
        pair_manifest_sha256=PAIR, limited_trial_installable=True,
        hardware_trial_approved=True, full_nes_installable=False, start_enabled=False,
        files={n: dict(bytes=len(b), sha256=digest(b), source_role=roles.get(n))
               for n, b in blobs.items()})
    blobs['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    a.out.mkdir(parents=True)
    archive = a.out/'NES111-80KiB-TRIAL-and-RESTORE044.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in blobs.items():
            info = zipfile.ZipInfo(n, date_time=(2026, 10, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, b)
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == len(blobs) and set(z.namelist()) == set(blobs)
        for n, b in blobs.items():
            assert z.read(n) == b, n
        assert not any('96.nh1' in n or 'banks32.nes' in n for n in z.namelist())
    result = dict(candidate=manifest['candidate'], zip_sha256=digest(archive.read_bytes()),
        zip_bytes=archive.stat().st_size, members=len(blobs), binary_roles=len(roles),
        pair_manifest_sha256=PAIR, limited_trial_installable=True,
        hardware_trial_approved=True, full_nes_installable=False,
        start_enabled=False, physical_result='pending', new_firmware=False, new_fpga=False)
    (a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    (a.out/'manifest.json').write_bytes(blobs['manifest.json'])
    shutil.copy2(__file__, a.out/'executed-release111.py')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
