# SPDX-License-Identifier: MIT
"""Frozen068 audit, requiring private raw evidence; no physical execution."""
from pathlib import Path
import argparse,json,re,tempfile
from nes_spi_boot import ROOT,sha
from nes_diag_safety import materialize,constraints
from nes_diag_io_budget import calculate

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def audit(e):
    e=e.resolve();meta=read(ROOT/'analysis/diag-safety-verification.json')
    assert sha(e/'manifest.json')==meta['manifest_sha256']
    m=read(e/'manifest.json');assert m['candidate']==meta['candidate'] and len(m['files'])==meta['archived_files']
    for n,h in m['files'].items():
        p=(e/n).resolve();assert p.is_relative_to(e) and sha(p)==h,n
    for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
    fit=read(e/'fit/result.json');wave=read(e/'wave/result.json');start=read(e/'startup/result.json');io=read(e/'io/result.json')
    assert fit['phases']==dict(map=0,fit=0,sta=0) and fit['identity']==0x68
    with tempfile.TemporaryDirectory(prefix='nes068-audit-') as d:
        out=Path(d);materialize(out);constraints(out)
        for n,h in fit['sources'].items():assert sha(out/n)==h,n
    for n,h in fit['sources'].items():
        assert sha(e/'fit'/n)==h,n
        if n.endswith('.sv'):assert wave['sources'][n]==h,n
    assert len(start['cases'])==4
    for c in start['cases']:
        raw=(e/'startup'/c['name']/'simulation.log').read_text(errors='replace')
        for n,h in c['sources'].items():assert sha(e/'startup'/c['name']/n)==h
        if c['expected_failure']:assert '** Fatal:' in raw and c['expected_failure'] in raw
        else:
            assert c['marker'] in raw and '** Fatal:' not in raw
            assert c['sources']['nes_diag_startup_guard.sv']==fit['sources']['nes_diag_startup_guard.sv']
    assert len(wave['cases'])==2
    for c in wave['cases']:
        raw=(e/'wave'/c['mode']/'simulation.log').read_text(errors='replace')
        assert c['marker'] in raw and not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',raw)
        assert 'CLOCK_HALT_COUNTEREXAMPLE locked_high_ce_low_over_8us=1' in raw
        assert sha(e/'wave'/c['mode']/'waveform.txt')==c['waveform_sha256']
    bad=read(e/'bypass/result.json');assert bad['expected_failure'] and bad['assertion']=='EARLY_MEMORY_READY'
    raw=(e/'bypass/load/simulation.log').read_text(errors='replace');assert '** Fatal:' in raw and bad['assertion'] in raw
    assert io['fit_result_sha256']==sha(e/'fit/result.json') and io['paths_sha256']==sha(e/'io/io-paths.tsv')
    inputs=read(e/'io/input-fit-inventory.json')
    for n,h in inputs.items():
        assert sha(e/'fit'/n)==h,n
        if n not in io['post_analysis_changed_inputs']:assert sha(e/'io'/n)==h,n
    assert set(io['post_analysis_changed_inputs'])<=set(['board.qsf','db/board.cmp.rdb','db/board.cycloneive_io_sim_cache.31um_ss_1200mv_85c_slow.hsd'])
    if 'board.qsf' in io['post_analysis_changed_inputs']:
        assert (e/'io/board.qsf').read_text()==(e/'fit/board.qsf').read_text()+'\nset_global_assignment -name LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"'
    for leg,name in [(20,'budget.json'),(60,'budget-outside.json')]:
        assert calculate(e/'io/io-paths.tsv',leg,5)==read(e/'io'/name)
    assert not read(e/'io/budget-outside.json')['scenario_positive']
    slacks=[float(v) for v in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',(e/'fit/output_files/board.sta.summary').read_text(encoding='latin1'),re.M)]
    assert len(slacks)==30 and min(slacks)==fit['internal_min_slack_ns']==meta['fit']['min_hold_ns']
    assert not meta['installable'] and not meta['external_io_signoff'] and not meta['hardware_execution']
    assert io['registered_read_controls'] and io['path_rows']==meta['io']['path_rows']
    memory=read(e/'memory/result.json');assert len(memory['cases'])==8
    total=0
    for c in memory['cases']:
        raw=(e/'memory'/c['name']/'simulation.log').read_text(errors='replace')
        for n,h in c['sources'].items():assert sha(e/'memory'/c['name']/n)==h
        if c['expected_failure']:
            assert '** Fatal:' in raw and c['expected_failure'] in raw
        else:
            assert c['marker'] in raw and '** Fatal:' not in raw and 'cancels=9' in c['marker']
            total+=c['total']
            for n in ['nes_rom_loader.sv','nes_rom_physical.sv','nes_rom_boot.sv']:assert c['sources'][n]==fit['sources'][n]
    assert total==meta['memory']['normal_bytes_each_write_read']==344064
    old=(e/'io-old-reader-failure.log').read_text(errors='replace')
    assert 'AssertionError' in old and '|reading_active' in old
    initial=read(e/'initial-verification-meta.json')
    assert initial['manifest_sha256']=='1f064615bd1e809188fce1cd201a8c87419e3127920cc936de0db46146f1081d'
    assert 'cannot be declared more than once' in (e/'initial-fit/map.log').read_text(errors='replace')
    print(f"PASS068 frozen={len(m['files'])} startup=4 bounded_C=2 bypass=1 memory=8 paths={io['path_rows']}; clock_halt_counterexample/open no_install")

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);audit(p.parse_args().evidence)
