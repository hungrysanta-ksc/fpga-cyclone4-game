# SPDX-License-Identifier: MIT
"""Read-only frozen071 evidence audit; private binaries/archives are required."""
from pathlib import Path
import argparse,json
from nes_cf68_pair_preflight import digest,verify,RBF_SHA,FIRMWARE_SHA,RAW
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def audit(e):
    meta=load(ROOT/'analysis/cf68-pair-verification.json');raw=(e/'manifest.json').read_bytes()
    assert digest(raw)==meta['manifest_sha256'];m=json.loads(raw)
    assert m['candidate']==meta['candidate'] and len(m['files'])==meta['archived_files']
    for n,h in m['files'].items():
        p=(e/n).resolve();assert p.is_relative_to(e.resolve()) and digest(p.read_bytes())==h,n
    pair=verify(e/'pair',meta['pair_manifest_sha256']);assert pair==meta['pair']
    assert digest((e/'pair'/RAW).read_bytes())==RBF_SHA
    assert digest((e/'firmware.stm').read_bytes())==FIRMWARE_SHA
    line=load(e/'input-lineage.json');assert line==load(ROOT/'analysis/cf68-pair-inputs.json')
    assert line['fpga_manifest_sha256']==digest((e/'reused068-manifest.json').read_bytes())
    old=load(e/'reused068-manifest.json')['files']
    assert line['inventory_sha256']==digest((e/'reused068-db-inventory.json').read_bytes())
    old_db=load(e/'reused068-db-inventory.json')
    assert line['database']=={n:h for n,h in old_db.items() if n.startswith('db/')} and len(line['database'])==114
    for n,h in line['fit_inputs'].items():
        assert old['fit/'+n]==h and digest((e/'assembly'/n).read_bytes())==h,n
    for n,h in line['fit_reports'].items():
        assert old['fit/'+n]==h,n
        if '.fit.' in n or '.sta.' in n or '.map.' in n:
            assert digest((e/'assembly'/n).read_bytes())==h,n
    for phase in ['asm','cpf']:
        log=(e/'assembly'/(phase+'-071.log')).read_text()
        assert 'successful. 0 errors, 0 warnings' in log and 'SC Standard Edition' in log and '25.1std.0 Build 1129' in log
    assembly=load(e/'assembly/assembly-071.json')
    assert assembly['input_lineage']==line and assembly['rbf_sha256']==RBF_SHA and assembly['rbf_bytes']==510856
    assert assembly['new_map_fit_sta'] is False and assembly['installable'] is False
    assert len(load(e/'excluded-incremental-inventory.json'))==17
    test=load(e/'tests/result.json');assert test['tests']==23 and test['failures']==test['errors']==test['skipped']==0 and test['physical_sd'] is False
    result=load(e/'programmer-final/result.json');assert result['raw_bytes']==510856 and result['raw_sha256']==RBF_SHA and result['negative_controls']==13
    assert result['mcu_manifest_sha256']==digest((e/'reused069-manifest.json').read_bytes())
    arm=load(e/'reused069-manifest.json')['files']
    for n in ['nes_diag_runtime.c','nes_diag_runtime.h','fpga.c']:
        assert digest((e/'programmer-final'/n).read_bytes())==arm['arm/src/'+n],n
    inc=(e/'programmer-final/nes_diag_fpga.inc').read_bytes()
    assert inc in (e/'programmer-final/fpga.c').read_bytes()
    for n,h in result['sources'].items():assert digest((e/'programmer-final'/n).read_bytes())==h,n
    assert 'compressed=212523 raw=510856 all_bytes=1' in (e/'programmer-final/programmer.log').read_text()
    assert 'negative_controls=13' in (e/'programmer-final/programmer.log').read_text()
    assert 'compressed=531 raw=66309 all_bytes=1' in (e/'programmer-boundaries-02.log').read_text()
    assert 'negative_controls=13' in (e/'programmer-boundaries-02.log').read_text()
    plan=load(e/'tests/test_12_candidate_restore_plan/rollback-plan.json')
    assert plan['read_only'] and not plan['executed'] and len(plan['actions'])==6
    for n,h in meta['public_sources'].items():
        assert digest((ROOT/n).read_bytes())==h and digest((e/'public-source'/n).read_bytes())==h,n
    print('PASS071 frozen='+str(len(m['files']))+' preflight23 / exact069 C510856+66309 / negatives13; no physical SD/install')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);audit(p.parse_args().evidence)
