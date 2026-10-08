# SPDX-License-Identifier: MIT
"""Audit frozen CF86 functional/routed evidence; no physical signoff."""
from pathlib import Path
import argparse,csv,hashlib,json,re
from nes_clock_audit086 import classify
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    e=p.parse_args().evidence.resolve()
    m=json.loads((ROOT/'analysis/clock086-verification.json').read_text())
    assert sha(e/'manifest.json')==m['manifest_sha256']
    inventory=json.loads((e/'manifest.json').read_text())['files']
    assert len(inventory)==m['archived_files']
    for n,h in inventory.items():
        q=(e/n).resolve();assert q.is_relative_to(e) and sha(q)==h,n
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    read=lambda n:json.loads((e/n).read_text())
    fit=read('fit03/result.json');wave=read('wave01/result.json')
    assert fit['identity_hex']=='86' and len(fit['summary_slacks'])==39 and min(fit['summary_slacks'])==0.158
    assert read('fit01/result.json')['minimum_reported_slack_ns']==-5.354
    for n,h in fit['sources'].items():assert sha(e/'fit03'/n)==h,n
    common=set(fit['sources'])&set(wave['sources']);assert len(common)==16
    for n in common:assert fit['sources'][n]==wave['sources'][n],n
    assert len(wave['cases'])==4 and sum(c['directed_cases'] for c in wave['cases'])==128
    assert sum(c['checked_response_bits'] for c in wave['cases'])==130360
    for i,c in enumerate(wave['cases']):
        log=(e/'wave01'/f"{i:02d}-{c['mode']}"/'simulation.log').read_text(errors='replace')
        assert not re.search(r'\*\* (Fatal|Error)(?:\s|:)',log)
        assert c['marker'] in log and c['max_abort_ns']<=5000 and c['max_ce_low_ns']<=8000
    with (e/'audit02/crossings.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    assert len(rows)==36 and classify(rows)=={'heartbeat_first_stage':12,'reset_release_async_clear':24}
    baseline=read('baseline-audit02/result.json');assert baseline['expected_failure']
    assert 'UNEXPECTED_CROSSING' in baseline['assertion']
    for n in ['bypass-guard','same-clock','nonsticky','synchronous-assert']:
        result=read(n+'01/result.json');assert result['mutation']==n and result['cases'][0]['expected_failure']
        log=(e/(n+'01')/'00-load/simulation.log').read_text(errors='replace')
        assert '** Fatal:' in log and result['cases'][0]['assertion'] in log
    budget=read('io01/budget.json');outside=read('io01/budget-outside.json')
    assert budget['path_rows']==3168 and min(budget['scenario_margin_ns'].values())==64.565
    assert outside['scenario_positive'] is False
    assert not m['installable'] and not m['hardware_execution'] and not m['external_io_signoff']
    print('PASS CF86: same16 RTL inputs;39 constrained summaries;36 classified crossings;128 faults/4 controls;IO3168. Physical/signoff=false')


if __name__=='__main__':main()
