# SPDX-License-Identifier: MIT
"""Audit local frozen CF85 evidence. Private060 inputs required for rerunning RTL."""
from pathlib import Path
import argparse, hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();e=a.evidence.resolve()
    meta=json.loads((ROOT/'analysis/clock-guard085-verification.json').read_text())
    assert sha(e/'manifest.json')==meta['manifest_sha256']
    manifest=json.loads((e/'manifest.json').read_text())
    assert len(manifest['files'])==meta['archived_files']
    for name,digest in manifest['files'].items():
        path=(e/name).resolve();assert path.is_relative_to(e)
        assert sha(path)==digest,name
    for name,digest in meta['public_sources'].items():assert sha(ROOT/name)==digest,name
    normal=json.loads((e/'normal02/result.json').read_text())
    assert normal['candidate']=='NES-CLOCK-GUARD-085' and normal['mutation'] is None
    assert len(normal['cases'])==4
    assert not any(normal[n] for n in ['hardware_execution','fit_sta_verified','external_io_signoff','both_clock_halt_safe','installable','full_spi_session'])
    assert sum(c['directed_cases'] for c in normal['cases'])==128
    assert sum(c['checked_response_bits'] for c in normal['cases'])==130360
    for i,c in enumerate(normal['cases']):
        assert c['max_abort_ns']<=5000 and c['max_ce_low_ns']<=8000
        log=(e/'normal02'/f"{i:02d}-{c['mode']}"/'simulation.log').read_text(errors='replace')
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
        assert c['marker'] in log and 'both_stop_counterexample=1' in log and 'PASS C_PREFIX085' in log
    for name,digest in normal['sources'].items():assert sha(e/'normal02'/name)==digest,name
    for name,digest in normal['executed_inputs'].items():assert sha(e/'normal02'/name)==digest,name
    for mutation in ['bypass-guard','same-clock','nonsticky']:
        folder=e/(mutation+'02');r=json.loads((folder/'result.json').read_text())
        assert r['mutation']==mutation and r['cases'][0]['expected_failure']
        log=(folder/'00-load/simulation.log').read_text(errors='replace')
        assert '** Fatal:' in log and r['cases'][0]['assertion'] in log
        for name,digest in r['sources'].items():assert sha(folder/name)==digest,name
    # Reuse claims apply only to unchanged generated files, never old timing slack.
    prior=json.loads((ROOT/'analysis/diag-safety-verification.json').read_text())['generated_sources']
    for name in meta['unchanged_cf68_generated_sources']:
        assert normal['sources'][name]==prior[name],name
    print('PASS CF85 archive; 4 GPIO cases / 128 directed faults / 3 causal controls; hardware/fit/install=false')


if __name__=='__main__':main()
