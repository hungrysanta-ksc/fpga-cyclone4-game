# SPDX-License-Identifier: MIT
"""Publish bounded PPU/collector diagnosis, never a game FPS or fix claim."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def inspect(path):
    r=read(path/'result.json');m=read(path/'inputs.json')
    assert r['completed'] and sha(path/'inputs.json')==r['inputs_SHA256']
    pins=read(ROOT/'analysis/boot493-verification.json')['FPGA']['source_inputs']
    for n,h in m['sources'].items():assert sha(path/n)==h==pins[n],n
    assert sha(path/'capture500_tb.sv')==m['testbench_SHA256']
    rows=[]
    for c,v in zip(m['cases'],r['results'],strict=True):
        assert c==v['case']
        assert (path/(c['name']+'.txt')).read_text()==''.join(' '.join(map(str,x))+'\n'for x in c['events'])
        log=path/(c['name']+'.log');assert sha(log)==v['log_SHA256']
        s=dict(x.split('=')for x in v['summary'].split())
        for k in s:s[k]=int(s[k],16 if k in ['errors','fetch','compact','raster','patch_errors']else 10)
        assert s['rows']==224 and s['exact_pixels']==s['patches']*256
        assert s['raster']==0
        if c['name']=='baseline':assert s['valid']==1 and s['errors']==s['patches']==0
        rows.append(dict(case=c,**s,log_SHA256=sha(log),
                         first_faults=re.findall(r'^# FETCH500 (.*)$',log.read_text(errors='replace'),re.M)))
    return dict(rows=rows,source_pins=m['sources'],inputs_SHA256=sha(path/'inputs.json'),
                result_SHA256=sha(path/'result.json'),testbench_SHA256=m['testbench_SHA256'],
                reference_SHA256=m['reference_SHA256'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['matrix','trace','phase','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    matrix,trace,phase=[inspect(x)for x in [a.matrix,a.trace,a.phase]]
    assert len(matrix['rows'])==19 and sum(x['valid'] for x in matrix['rows'])==13
    assert sum(x['exact_pixels']for x in matrix['rows'])==9216
    for x in trace['rows']:
        old=next(y for y in matrix['rows']if y['case']['name']==x['case']['name'])
        assert all(x[k]==old[k]for k in ['valid','fetch','patches','exact_pixels','first_y','first_x'])
    unique=matrix['rows']+phase['rows']
    assert len({x['case']['name']for x in unique})==len(unique)==24
    result=dict(experiment=500,merged_PR138='7e9699fb5d3ce4617495c204aa04d194cb09798d',
      branch='codex/nes-capture-correctness-500',physical_baseline='MMC493',
      investigation_executed=True,A1_complete=False,production_RTL_changed=False,
      matrix=matrix,trace=trace,phase=phase,
      unique_conditions=len(unique),rejected_conditions=sum(not x['valid']for x in unique),
      reproduced_fetch_signatures=sorted(set(x['fetch']for x in unique if not x['valid'])),
      new_Questa_run=True,license_seats=1,sequential_execution=True,new_Quartus_run=False,
      new_installer=False,new_physical_FPS=None,
      first_failed_attempts=[dict(name='test01',reason='Missing Intel altsyncram simulation library;no behavioral result'),
                            dict(name='test02',reason='Fixture connected ALE/address-valid instead of ROM data-valid;baseline failed;stopped;excluded')],
      scope='Actual493 PPU and collector RTL,recorded179 PPUMASK/optional2006 write boundaries,deterministic always-ready external memory;no CPU/MMC3/PSRAM/full-game replay. Offsets are phase sensitivity,not matched physical time. Raw pixels compared to independent post-CE observer of this PPU,not complete SNES output.',
      next='Implement row-boundary recovery only after complete raw-row ownership;retain ROM/data-valid/address/lane faults,missing pixels,raw capacity,STOP and final query/ACK gates. A1 remains open until corrected path and guards pass.',
      sources={n:sha(ROOT/n)for n in ['tools/test_nes_capture500.py','tools/analyze_nes_capture500.py',
          'tests/nes-functional/patch_ppu181_tb.sv','analysis/boot493-verification.json']})
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k]for k in ['unique_conditions','rejected_conditions','reproduced_fetch_signatures','A1_complete','production_RTL_changed']}))
