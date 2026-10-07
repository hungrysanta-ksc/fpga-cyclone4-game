# SPDX-License-Identifier: MIT
"""Audit frozen067 private evidence and current public source; no new execution."""
from pathlib import Path
import argparse, hashlib, json, re, tempfile
from nes_diag_memory_timing import materialize, constraints

ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))

def audit(e):
    e=e.resolve()
    meta=read(ROOT/'analysis/diag-memory-verification.json')
    assert sha(e/'manifest.json')==meta['manifest_sha256']
    manifest=read(e/'manifest.json')
    assert manifest['candidate']==meta['candidate']
    assert len(manifest['files'])==meta['archived_files']
    for name,h in manifest['files'].items():
        p=(e/name).resolve()
        assert p.is_relative_to(e) and sha(p)==h,name
    for name,h in meta['public_sources'].items():
        assert sha(ROOT/name)==h,name
    unit,wave,fit=[read(e/n/'result.json') for n in ['unit','wave','fit']]
    assert len(unit['cases'])==8 and len(wave['cases'])==2
    for c in unit['cases']:
        folder=e/'unit'/c['name']
        raw=(folder/'simulation.log').read_text(errors='replace')
        for n,h in c['sources'].items(): assert sha(folder/n)==h,n
        if c['expected_failure']:
            assert '** Fatal:' in raw and c['expected_failure'] in raw
        else:
            assert c['marker'] in raw and 'cancels=9' in c['marker']
            assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',raw)
            assert f"FULL_MEMORY total={c['total']} writes={c['total']} reads={c['total']}" in raw
            for n in ['nes_rom_loader.sv','nes_rom_physical.sv','nes_rom_boot.sv']:
                assert c['sources'][n]==fit['sources'][n]
    for c in wave['cases']:
        folder=e/'wave'/c['mode']
        raw=(folder/'simulation.log').read_text(errors='replace')
        assert c['marker'] in raw and not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',raw)
        assert sha(folder/'waveform.txt')==c['waveform_sha256']
    for n,h in fit['sources'].items():
        assert sha(e/'fit'/n)==h,n
        if n.endswith('.sv'): assert wave['sources'][n]==h,n
    for n,h in wave['sources'].items(): assert sha(e/'wave'/n)==h,n
    for key,file in [('driver_sha256','executed-driver.py'),('materializer_sha256','executed-materializer.py')]:
        assert sha(e/'wave'/file)==wave[key]
    summary=(e/'fit/output_files/board.sta.summary').read_text(encoding='latin1')
    slacks=[float(s) for s in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',summary,re.M)]
    assert len(slacks)==30 and min(slacks)==0.150==fit['internal_min_slack_ns']
    assert fit['phases']=={'map':0,'fit':0,'sta':0}
    assert not fit['external_io_constrained'] and not fit['hardware_eligible']
    assert not meta['installable'] and not meta['full_spi_session'] and not meta['hardware_execution']
    # Current generator, including all inherited templates, must reproduce fit inputs.
    with tempfile.TemporaryDirectory(prefix='nes067-audit-') as d:
        out=Path(d);files=materialize(out);constraints(out)
        for n in files+['board.qsf','board.sdc','gbc_bus_pll0.v']:
            assert sha(out/n)==fit['sources'][n],n
    print(f"PASS067 frozen={len(manifest['files'])} normal=4 negatives=4 bounded_C=2 internal_STA=30; external_IO/open no_install")

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    audit(p.parse_args().evidence)
