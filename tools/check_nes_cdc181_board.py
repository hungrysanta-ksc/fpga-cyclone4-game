# SPDX-License-Identifier: MIT
"""Separate routed feasibility, scoped CDC/IO checks and actual-clock approval."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from check_nes_boundary165 import measurements

def main():
    p=argparse.ArgumentParser()
    for n in ['fit','route','scope','cdc','test','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();load=lambda p:json.loads(p.read_bytes())
    m=load(a.fit/'preparation.json');r=load(a.route/'preparation.json');assert m==r
    baseline=load(ROOT/'analysis/rank181-verification.json')['verification']['sources']
    assert baseline==m['baseline_sources'] and len(baseline)==68
    for n,h in m['sources'].items():
        assert sha(a.fit/n)==sha(a.route/n)==h,n
        if n not in ('board.sdc','cdc181.sdc'):assert baseline[n]==h,n
    assert m['changed']==['board.sdc'] and m['added']==['cdc181.sdc']
    assert sha(ROOT/'tools/nes_cdc181.py')==m['preparer_sha256']
    # The original routed DB was never opened for analysis. TimeQuest uses a copy.
    origins=load(a.route/'route-inputs.json')
    for n,h in origins.items():
        if n in ('map.log','map.exitcode'):continue # copied from fresh map01
        assert sha(a.fit/n)==h,('original FIT changed',n)
    route_changes=[n for n,h in origins.items() if sha(a.route/n)!=h]
    allowed={'db/board.cmp.hdb','db/board.cmp.rdb','db/board.taw.rdb','db/board.tis_db_list.ddb',
             'db/board.cycloneive_io_sim_cache.31um_ff_1200mv_0c_fast.hsd'}
    assert set(route_changes)<=allowed,route_changes
    for n in ['fit.exitcode']:
        assert int((a.fit/n).read_text(encoding='utf-8-sig'))==0
    for n in ['check-cdc181.exitcode','timing181.exitcode','io181-02.exitcode','critical181.exitcode']:
        assert int((a.route/n).read_text(encoding='utf-8-sig'))==0,n
    log=(a.fit/'fit.log').read_text(errors='replace');assert 'Fitter was successful' in log
    assert 'Fitter failed to route' not in log
    report=(a.fit/'output_files/board.fit.rpt').read_text(encoding='latin1')
    def count(label):return int(re.search(r'; '+re.escape(label)+r'\s*; ([\d,]+) /',report)[1].replace(',',''))
    hold=[]
    for line in report.split('; Estimated Delay Added for Hold Timing Summary',1)[1].split('\n\n',1)[0].splitlines():
        f=[v.strip() for v in line.split(';')][1:-1]
        if len(f)==3 and re.fullmatch(r'\d+\.\d+',f[2]):hold.append(dict(source=f[0],destination=f[1],sum_ns=float(f[2])))
    scope=load(a.scope);cdc=load(a.cdc);test=load(a.test/'result.json')
    assert scope['passed'] and scope['scope']['unexpected_removed']==0
    assert cdc['passed'] and cdc['routed_approval'] and not cdc['whole_design_timing_approval']
    assert test['passed'] and test['late_payload_rejected'] and test['rtl_sha256']==m['sources']['nes_native_mailbox165.sv']
    assert test['runner_sha256']==sha(ROOT/'tools/test_nes_cdc181.py')
    timing={}
    for view in ['implementation','nominal']:
        xs=list(csv.DictReader((a.route/(view+'-clocks181.tsv')).open(),delimiter='\t'))
        assert len({x['corner'] for x in xs})==3 and len({x['from_clock'] for x in xs})==4
        assert any(x['from_clock']!=x['to_clock'] for x in xs)
        worst=lambda k:min((x for x in xs if x['kind']==k),key=lambda x:float(x['slack']))
        timing[view]=dict(rows=len(xs),passed=all(float(x['slack'])>=0 for x in xs),
                         worst_setup=worst('setup'),worst_hold=worst('hold'),
                         worst_related=min((x for x in xs if x['kind']=='setup' and x['from_clock']!=x['to_clock']),key=lambda x:float(x['slack'])))
    assert (a.route/'nominal181.sdc').read_text().endswith('source cdc181.sdc\n')
    io=measurements(a.route)
    physical=timing['nominal']['passed'] and cdc['passed'] and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
    stats={}
    for name in ['memory','related']:
        s=(a.route/('critical181-'+name+'.rpt')).read_text(encoding='latin1')
        n=int(re.search(r'; Number of Logic Levels\s*;\s*; (\d+)',s)[1])
        data=s.split(';   Data ',1)[1].split(';  Required Path',1)[0]
        route=re.search(r';    Routing Element\s*;\s*; (\d+)\s*; ([\d.]+)\s*; (\d+)',data)
        stats[name]=dict(logic_levels=n,routing_elements=int(route[1]),routing_delay_ns=float(route[2]),routing_percent=int(route[3]))
    public=['tools/nes_cdc181.py','tools/nes_cdc181_inventory.tcl','tools/check_nes_cdc181.py',
            'tools/test_nes_cdc181.py','tools/nes_cdc181_timing.py','tools/check_nes_cdc181_board.py']
    result=dict(evidence_verified=True,fit_pass=True,le=count('Total logic elements'),
                labs=count('Total LABs:  partially or completely used'),m9k=count('M9Ks'),
                rtl_unchanged=True,sources=m['sources'],scope=scope,cdc=cdc,functional=test,
                timing=timing,conditional_io=io,critical_path_stats=stats,
                hold_added_summary=hold,hold_added_sum_ns=round(sum(x['sum_ns'] for x in hold),3),
                original_fit_preserved_files=len(origins)-2,sta_copy_changed_files=route_changes,
                actual_clock_pass=timing['nominal']['passed'],adopted=physical,new_package=False,hardware=False,fps60=False,
                public_sources={n:sha(ROOT/n) for n in public})
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ['fit_pass','le','labs','m9k','actual_clock_pass','adopted','hold_added_sum_ns']}))

if __name__=='__main__':main()
