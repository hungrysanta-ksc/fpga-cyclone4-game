# SPDX-License-Identifier: MIT
"""Audit061 saved evidence; does not execute HDL or qualify a physical board."""
from pathlib import Path
import argparse, hashlib, json, re

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    root=a.evidence.resolve();manifest=json.loads((root/'manifest.json').read_text())
    for name,digest in manifest['files'].items():
        path=(root/name).resolve();assert path.is_relative_to(root),name
        assert path.is_file() and sha(path)==digest,name
    fit=json.loads((root/'fit-03/result.json').read_text())
    wave=json.loads((root/'wave-02/result.json').read_text())
    assert fit['physical_pin_assignments']==135 and fit['internal_timing_pass']
    assert fit['internal_min_slack_ns']==0.131 and not fit['hardware_eligible']
    assert len(wave['cases'])==2 and [c['mode'] for c in wave['cases']]==['load','check']
    for name,digest in fit['sources'].items():
        assert sha(root/'fit-03'/name)==digest
        if name.endswith('.sv'):assert wave['sources'][name]==digest,name
    for name,digest in wave['sources'].items():assert sha(root/'wave-02'/name)==digest,name
    assert sha(root/'fit-03/executed-driver.py')==fit['driver_sha256']
    assert sha(root/'wave-02/executed-driver.py')==wave['driver_sha256']
    assert sha(root/'wave-02/executed-materializer.py')==wave['materializer_sha256']==fit['driver_sha256']
    for mode,bits in [('load',29024),('check',43288)]:
        log=(root/'wave-02'/mode/'simulation.log').read_text(errors='replace')
        assert f'checked={bits}' in log and 'start_barriers=2 no_RUN=1' in log
        assert not re.search(r'\*\* (?:Fatal|Error):',log)
    for mutation,message in [('fast-memory','WRITE pulse too short'),('allow-start','061 START rejection missing'),('connected-start','Unexpected RUN')]:
        suffix='02' if mutation=='fast-memory' else '01'
        folder=root/('mutation-'+mutation+'-'+suffix);r=json.loads((folder/'result.json').read_text())
        assert r['expected_failure'] and r['assertion']==message
        assert message in (folder/'load/simulation.log').read_text(errors='replace')
    old=(root/'fit-02/output_files/board.sta.summary').read_text()
    assert 'Slack : -0.487' in old,'Preserve actual initial hold failure'
    print(f'PASS061 saved evidence: {len(manifest["files"])} files; identical production RTL; two GPIO phases; three causal failures; internal STA only')

if __name__=='__main__':main()
