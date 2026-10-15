# SPDX-License-Identifier: MIT
"""Check failed routing without treating partial placement as successful FIT."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_palette181 import raster

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','fit','test','join','bits','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();load=lambda p:json.loads(p.read_bytes())
    m=load(a.fit/'preparation.json');old=load(ROOT/'analysis/board181-verification.json')
    assert set(m['sources'])==set(old['verification']['fits']['map03']['sources'])
    for n,h in m['sources'].items():
        assert sha(a.fit/n)==h,n
        assert sha(a.baseline/n)==old['verification']['fits']['map03']['sources'][n],n
        if n!='nes_native_raster181.sv':assert sha(a.baseline/n)==h,n
    assert (a.fit/'nes_native_raster181.sv').read_text()==raster((a.baseline/'nes_native_raster181.sv').read_text())
    assert m['preparer_sha256']==sha(ROOT/'tools/nes_palette181.py')
    t=load(a.test/'result.json');j=load(a.join/'result.json')
    assert t['passed'] and j['passed'] and t['equivalent_cycles']==3287929 and t['copy_checks']==384
    for v in [t,j]:
        for n,h in v['sources'].items():assert m['sources'][n]==h,n
    assert t['runner_sha256']==sha(ROOT/'tools/test_nes_palette181.py')
    assert j['runner_sha256']==sha(ROOT/'tools/test_nes_board181_join.py')
    assert sha(a.bits/'nes_native_raster181.sv')==m['sources']['nes_native_raster181.sv']
    assert sha(a.bits/'palette181_tb.sv')==sha(ROOT/'tests/nes-functional/palette181_tb.sv')
    bitlog=(a.bits/'vsim.log').read_text(errors='replace')
    assert 'PASS PALETTEBITS181 patterns=194 checks=18624 inspections=582' in bitlog
    assert not re.search(r'\*\* (Error|Fatal):',bitlog)
    log=(a.fit/'fit.log').read_text();rpt=(a.fit/'output_files/board.fit.rpt').read_text(encoding='latin1')
    assert 'Fitter placement was successful' in log and 'Fitter was unsuccessful' in log
    assert 'requires 965 LABs' in log and 'device contains only 963 LABs' in log
    assert 'Info (188005)' in log and 'following 75 routing resource(s)' in log
    def count(label):return int(re.search(r'; '+re.escape(label)+r'\s*; ([\d,]+) /',rpt)[1].replace(',',''))
    signals=re.findall(r'Info \(170139\): Signal "([^"]+)"',log);assert len(signals)==79
    hold=[];details=[]
    for title,table in [('Summary',hold),('Details',details)]:
        section=rpt.split('; Estimated Delay Added for Hold Timing '+title,1)[1].split('\n\n',1)[0]
        for line in section.splitlines():
            fields=[x.strip() for x in line.split(';')][1:-1]
            if len(fields)==3 and re.fullmatch(r'\d+\.\d+',fields[2]):
                table.append(dict(source=fields[0],destination=fields[1],added_delay_ns=float(fields[2])))
    assert len(hold)==4 and len(details)>=40
    sdc=(a.fit/'board.sdc').read_text()
    assert 'create_clock -name board8 -period 125 [get_ports CLKIN]' in sdc
    assert 'create_clock -name nes -period 45.454 [get_ports SNES_SYSCLK]' in sdc
    assert not any(x in sdc for x in ['set_clock_groups','set_false_path','set_min_delay'])
    fit=dict(synthesis_pass=True,placement_pass=True,routing_pass=False,fit_pass=False,
        partial_le=count('Total logic elements'),required_labs=count('Total LABs:  partially or completely used'),m9k=count('M9Ks'),
        available_labs=963,unrouted_signals=signals,unrouted_oam_signals=sum('OAMEval:spriteeval|' in n for n in signals),
        conflicting_routing_resources=75,hold_delay_summary=hold,hold_delay_details=details,
        hold_delay_sum_ns=round(sum(v['added_delay_ns'] for v in hold),3),
        fit_report_sha256=sha(a.fit/'output_files/board.fit.rpt'),fit_log_sha256=sha(a.fit/'fit.log'),
        scope='Failed routing/automatic retry. Counts are partial, NOT a routed implementation. Hold delay sums are router additions across nets, NOT slack. No STA/IO/ASM approval.')
    public=['tools/nes_palette181.py','tools/test_nes_palette181.py','tools/check_nes_palette181_route.py',
        'tools/test_nes_board181_join.py','tests/nes-functional/palette181_tb.sv']
    result=dict(evidence_verified=True,passed=False,fit=fit,sources=m['sources'],collector=t,board_join=j,
        palette_bits=dict(patterns=194,storage_checks=18624,inspections=582,log_sha256=sha(a.bits/'vsim.log')),
        public_sources={n:sha(ROOT/n) for n in public},adopted=False,hardware=False,fps60=False,new_package=False,
        next='Inventory each CDC protocol before constraints: first synchronizer stages, held payload with bounded delay, and resets. Preserve same-clock checks and source/ACK ownership. No blanket clock cut, hold-off FIT, seed loop or fabricated timing pass.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(evidence_verified=True,fit_pass=False,le=fit['partial_le'],labs=fit['required_labs'],unrouted_oam=fit['unrouted_oam_signals'],hold_sum=fit['hold_delay_sum_ns'])))

if __name__=='__main__':main()
