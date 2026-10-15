# SPDX-License-Identifier: MIT
"""Keep functional, scoped CDC, FIT, actual-clock and IO results separate."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from check_nes_boundary165 import measurements

def main():
    p=argparse.ArgumentParser()
    for n in ['fit','route','scope','test','checks','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    load=lambda p:json.loads(p.read_bytes())
    m=load(a.fit/'preparation.json');assert m==load(a.route/'preparation.json')
    for n,h in m['sources'].items():assert sha(a.fit/n)==sha(a.route/n)==h,n
    changed={n for n,h in m['sources'].items() if h!=m['baseline_cdc_sources'][n]}
    assert changed=={'nes_rom_physical.sv','cdc181.sdc'} and len(m['sources'])==69
    assert sha(ROOT/'tools/nes_replyjoin181.py')==m['preparer_sha256']
    t=load(a.test/'result.json');assert t['passed'] and t['candidate_sha256']==m['sources']['nes_rom_physical.sv']
    assert sha(a.test/'result.json')==m['reply_join_result_sha256']
    assert t['runs']['baseline']==t['runs']['candidate']==t['runs']['delay9'] and t['runs']['wrong_capture']['rejected']
    for n,h in t['executed_sources'].items():assert sha(a.test/n)==h,n
    for n in ['nes_rom_service.sv','nes_native_arbiter165.sv','nes_native_fill165.sv']:assert t['executed_sources'][n]==m['sources'][n]
    for n in ['rom_physical_model.sv','reply181_join_tb.sv']:assert sha(ROOT/'tests/nes-functional'/n)==t['executed_sources'][n]
    assert sha(ROOT/'tools/test_nes_replyjoin181.py')==t['runner_sha256']
    for n in ['map','fit']:assert int((a.fit/(n+'.exitcode')).read_text(encoding='utf-8-sig'))==0
    for n in ['timing181','check-cdc181','check-reply181','io181','critical-reply181']:
        assert int((a.route/(n+'.exitcode')).read_text(encoding='utf-8-sig'))==0,n
    origins=load(a.route/'route-inputs.json');mutated=[]
    for n,h in origins.items():
        assert sha(a.fit/n)==h,('FIT original changed',n)
        if sha(a.route/n)!=h:mutated.append(n)
    allowed={'db/board.cmp.hdb','db/board.cmp.rdb','db/board.taw.rdb','db/board.tis_db_list.ddb',
             'db/board.cycloneive_io_sim_cache.31um_ff_1200mv_0c_fast.hsd'}
    assert set(mutated)<=allowed,mutated
    rows=lambda p:list(csv.DictReader(p.open(),delimiter='\t'))
    keys=lambda n:{tuple(x.values()) for x in rows(a.scope/n)}
    b=keys('scope181-before.tsv');c=keys('scope181-after.tsv');removed=b-c
    pairs={(x['source'],x['destination']) for x in m['reply_selected']}
    assert len(removed)==8 and not c-b and all(x[0]=='hold' and (x[3],x[4]) in pairs for x in removed)
    reply=load(a.checks/'reply-routed01.json');cdc=load(a.checks/'cdc-routed01.json')
    assert reply['physical_pass'] and cdc['passed'] and cdc['routed_approval']
    assert reply['sources']==m['sources'] and reply['checker_sha256']==sha(ROOT/'tools/check_nes_replyjoin181.py')
    for n,h in cdc['files'].items():assert sha(a.route/n)==h,n
    report=(a.fit/'output_files/board.fit.rpt').read_text(encoding='latin1')
    assert 'Fitter was successful' in (a.fit/'fit.log').read_text(errors='replace')
    count=lambda label:int(re.search(r'; '+re.escape(label)+r'\s*; ([\d,]+) /',report)[1].replace(',',''))
    def utilization(label):
        line=next(x for x in report.splitlines() if label in x)
        return [float(x) for x in re.findall(r'(\d+\.\d+)%',line)]
    timing={}
    for view in ['implementation','nominal']:
        xs=rows(a.route/(view+'-clocks181.tsv'))
        assert len({x['corner'] for x in xs})==3 and len({x['from_clock'] for x in xs})==4
        setup=[x for x in xs if x['kind']=='setup'];worst=lambda v:min(v,key=lambda x:float(x['slack']))
        timing[view]=dict(rows=len(xs),passed=all(float(x['slack'])>=0 for x in xs),
            worst_setup=worst(setup),worst_hold=worst([x for x in xs if x['kind']=='hold']),
            worst_related=worst([x for x in setup if x['from_clock']!=x['to_clock']]),
            worst_same=worst([x for x in setup if x['from_clock']==x['to_clock']]))
    io=measurements(a.route)
    baseline=load(ROOT/'analysis/cdc181-verification.json')
    for n,h in baseline['public_sources'].items():assert sha(ROOT/n)==h,n
    public=['tools/nes_replyjoin181.py','tools/test_nes_replyjoin181.py','tools/check_nes_replyjoin181.py',
            'tools/check_nes_replyboard181.py','tools/nes_reply181_scope.tcl','tests/nes-functional/reply181_join_tb.sv']
    result=dict(evidence_verified=True,selected='replyjoin181/map02+scope01+route01+test03',fit_pass=True,
        le=count('Total logic elements'),labs=count('Total LABs:  partially or completely used'),m9k=count('M9Ks'),
        routing=dict(average_total_h_v=utilization('Average interconnect usage'),peak_total_h_v=utilization('Peak interconnect usage')),
        sources=m['sources'],changed=sorted(changed),functional=t,reply=reply,prior_cdc=cdc,
        scope=dict(before=len(b),after=len(c),removed_hold_pairs=8,unexpected_removed=0,reset_unchanged=True,related_pll_unchanged=True),
        timing=timing,conditional_io=io,original_fit_files_preserved=len(origins),sta_copy_changed_files=mutated,
        baseline_evidence_sha256=sha(ROOT/'analysis/cdc181-verification.json'),
        actual_clock_pass=timing['nominal']['passed'],adopted=False,new_package=False,hardware=False,fps60=False,
        public_sources={n:sha(ROOT/n) for n in public},
        failed_attempts={'test01':'fixture identifier used SystemVerilog priority keyword; compile failure',
            'test02':'baseline fixture clear pulse did not span a sampling edge; abort check failed, RTL unchanged',
            'map01':'preparer CRLF hash assertion failed; MAP inadvertently ran on partial preparation, no FIT; excluded',
            'test03/map02':'selected; LF reader bytes match prior tested candidate; all job exit codes checked'})
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ['fit_pass','le','labs','m9k','routing','actual_clock_pass','adopted','original_fit_files_preserved']}))

if __name__=='__main__':main()
