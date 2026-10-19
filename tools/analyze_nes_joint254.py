# SPDX-License-Identifier: MIT
"""Same-boundary FSM diagnosis, fused query/context cost, conditional schedule."""
from pathlib import Path
import argparse,csv,json,re,shutil
from nes_delta231 import BASE,sha
from analyze_nes_joint253 import area


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('out','test','incremental','map','fsm-test','fsm-map'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(f):
        pins[f.relative_to(BASE).as_posix()]=sha(f);return f
    def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
    def rows(f):return list(csv.DictReader(pin(f).open(encoding='utf-8')))
    def run(path):
        r=read(path/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(pin(path/n))==h
        for n,h in r['input_hashes'].items():
            source=BASE/n
            # A diagnostic preserves its generator before the joint candidate
            # was added. Verify that captured file, not a later working copy.
            if sha(source)!=h:
                source=path/source.name
            assert sha(pin(source))==h,(path,n)
        return r
    test=run(a.test);inc=run(a.incremental);mapped=run(a.map)
    ft=run(a.fsm_test);fm=run(a.fsm_map)
    assert test['frames']==71 and test['guards']==list(range(1,22))
    assert inc['frames']==4 and inc['incremental_shadow_granules']==8
    assert test['rtl_hashes']==inc['rtl_hashes']==mapped['rtl_hashes']
    assert ft['rtl_hashes']==fm['rtl_hashes'] and ft['frames']==3
    prior=BASE/'probes/nes-joint253'
    old=read(prior/'analysis01/result.json')
    old_test=read(prior/'test07/result.json')
    # Bounded causal diagnostic: ignoring module names, precisely one RTL
    # expression changed. No synthesis attribute, seed or state width changed.
    for n in ft['rtl_hashes']:
        oldname=n.replace('254','253')
        before=pin(prior/'test07'/oldname).read_text()
        after=pin(a.fsm_test/n).read_text().replace('254','253')
        if n=='nes_core254.sv':
            after=re.sub(r'assign output_phase=state==V_CLEARALL.*?;', 'assign output_phase=state>=V_CLEARALL;',after)
        assert before==after,n
    for name in ('cycles.csv','output-cycles.csv'):
        assert rows(a.fsm_test/name)==rows(prior/'test07'/name)[:3]
    assert pin(prior/'test07'/'blocks.txt').read_text().splitlines()[:ft['blocks']]==pin(a.fsm_test/'blocks.txt').read_text().splitlines()
    def hierarchy(path):
        text=pin(path).read_text();result={}
        for line in text.splitlines():
            if not line.startswith(';'):continue
            c=[v.strip() for v in line.split(';')]
            if len(c)>4 and c[1].startswith('|nes_') and re.fullmatch(r'\d+ \(\d+\)',c[2]):
                result[c[1]]=dict(comb=int(c[2].split()[0]),own_comb=int(re.search(r'\((\d+)\)',c[2])[1]),
                                  FF=int(c[3].split()[0]),own_FF=int(re.search(r'\((\d+)\)',c[3])[1]))
        return result
    def fsm(path):
        s=pin(path).read_text();return sorted(set(re.findall(r'State Machine - (\|[^\s;]+)',s)))
    before=old['area_after'];diagnostic=area(fm['summary']);after=area(mapped['summary'])
    tables=dict(prior=fsm(prior/'map02/output_files/joint.map.rpt'),diagnostic=fsm(a.fsm_map/'output_files/joint.map.rpt'),joint=fsm(a.map/'output_files/joint.map.rpt'))
    assert len(tables['prior'])==1 and ':reader|' in tables['prior'][0]
    assert len(tables['diagnostic'])==2 and any(':encoder|' in n for n in tables['diagnostic'])
    assert len(tables['joint'])==1 and ':encoder|' in tables['joint'][0]
    assert after['bits']==before['bits']==diagnostic['bits']==49152
    assert len(mapped['ram_rows'])==4 and any('True Dual Port' in row and '1024' in row for row in mapped['ram_rows'])
    src={int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(a.test/'cycles.csv')}
    out={int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(a.test/'output-cycles.csv')}
    oldsrc={int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(prior/'test07/cycles.csv')}
    oldout={int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(prior/'test07/output-cycles.csv')}
    detail=[]
    for f in range(905,976):
        s=src[f];o=out[f];b=oldsrc[f];bo=oldout[f]
        assert s['queries']==b['queries'] and s['transfer']==b['transfer']
        assert o['transport_crc_cycles']==bo['transport_crc_cycles']
        assert o['total']-bo['total']==66
        detail.append(dict(frame=f,source_total_cycles=s['total'],source_prepare_cycles=s['prepare'],
          source_blocked_cycles=s['blocked'],source_ackwait_cycles=s['ackwait'],queries=s['queries'],
          wirebytes_cumulative=s['wirebytes_cumulative'],source_delta_cycles=s['total']-b['total'],
          prepare_delta_cycles=s['prepare']-b['prepare'],output_cycles=o['total'],output_delta_cycles=o['total']-bo['total'],
          hash_state_cycles=o['hash_states'],source_ms=s['total']/22000,output_ms=o['total']/22000,
          combined_ms=(s['total']+o['total'])/22000))
    assert pin(a.test/'blocks.txt').read_bytes()==pin(prior/'test07/blocks.txt').read_bytes()
    schedules=[]
    for oldrow in old['rows']:
        f=oldrow['frame'];di=(src[f]['total']-oldsrc[f]['total'])/22000;do=(out[f]['total']-oldout[f]['total'])/22000
        total=oldrow['total_ms']+di+do
        schedules.append(dict(frame=f,setup=oldrow['setup'],retained_policy=oldrow['retained_policy'],
            old253_ms=oldrow['total_ms'],measured_input_delta_ms=di,measured_output_delta_ms=do,
            total_ms=total,residual_ms=1000/60-total))
    summaries=[]
    for setup in (500,1000):
        for policy in ('command_tail','only_bitmap_removed'):
            rr=[r for r in schedules if r['setup']==setup and r['retained_policy']==policy]
            worst=max(rr,key=lambda r:r['total_ms'])
            summaries.append(dict(setup=setup,retained_policy=policy,max_ms=worst['total_ms'],
              min_residual_ms=worst['residual_ms'],worst_frame=worst['frame'],over=[r['frame'] for r in rr if r['residual_ms']<0]))
    warm=detail[2:]
    fields=('source_total_cycles','source_prepare_cycles','source_delta_cycles','prepare_delta_cycles',
            'output_cycles','output_delta_cycles','hash_state_cycles','source_ms','output_ms','combined_ms')
    result=dict(passed=True,stage=254,scope=__doc__,
        test={k:v for k,v in test.items() if k!='input_hashes'},incremental={k:v for k,v in inc.items() if k!='input_hashes'},
        area_240=old['area_before'],area_253=before,area_fsm=diagnostic,area_joint=after,
        delta_fsm={k:diagnostic[k]-before[k] for k in before},delta_joint_from_fsm={k:after[k]-diagnostic[k] for k in before},
        delta_joint_from_253={k:after[k]-before[k] for k in before},
        fsm_tables=tables,
        fsm_diagnostic=dict(only_phase_expression_changed=True,three_frame_cycles_and_bytes_exact=True,
            conclusion='Replacing the numeric state ordering predicate with explicit state equality membership restores core FSM extraction under the same Quartus settings.'),
        hierarchy_fsm=hierarchy(a.fsm_map/'output_files/joint.map.rpt'),hierarchy_joint=hierarchy(a.map/'output_files/joint.map.rpt'),
        memory_rows=mapped['ram_rows'],context_RAM=[832,863],extra_certificate_wire_bytes=0,
        warm_bounds={k:[min(r[k] for r in warm),max(r[k] for r in warm)] for k in fields},
        mean_source_delta_ms=sum(r['source_delta_cycles'] for r in warm)/len(warm)/22000,
        source_faster_frames=sum(r['source_delta_cycles']<0 for r in warm),source_slower_frames=sum(r['source_delta_cycles']>0 for r in warm),
        final_source_wire_delta_bytes=src[975]['wirebytes_cumulative']-oldsrc[975]['wirebytes_cumulative'],
        payload_and_blocks_exact_253=True,summaries=summaries,rows=schedules,frames_detail=detail,input_hashes=pins,
        limitations=[
          'Standalone MAP, no wholeboard FIT, placement or STA. The old 490LE/40LAB deficit is not reduced by this boundary subtraction.',
          'FSM-only extraction diagnosis is isolated; subsequent query fusion and context RAM are compared jointly, not individually attributed.',
          'One source cursor now controls queries. Removal of independent query prefetch increases preparation/service time; SPI status polling can also change.',
          'Certificate wire bytes are staged once before output begin, then reread internally. New packet framing/adapter/control and actual ARM scheduling costs remain unknown.',
          'Context display-base is validated against current serial, not actual per-bank SNES display retirement history.',
          'Output bytes/ranges/display ACK remain fixtures. No new ARM N5 restoration/planner RUN, SNES execution, MCU hardware cycles or physical60fps.',
          'All71 actual frames have raw2. No new integrated raw0 transition run; earlier250 coverage is preserved.',
          'Conditional schedules replace only measured253 boundary terms and retain ARM32000cycles,32 certificate bytes, parser allocations and conditional SNES validate181 removal.',
          'Capture readiness precedes measured source time. NES frame execution/capture and actual final-display lease overlap remain outside the timing experiment.',
          'CRC16 detects corruption but provides neither authentication nor collision-free equivalence.'])
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    summary={k:v for k,v in result.items() if k not in ('input_hashes','rows','frames_detail')}
    summary.update(input_count=len(pins),private_result_sha256=sha(d/'result.json'))
    (d/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    for name,rr in [('frames.csv',detail),('schedules.csv',schedules)]:
        with (d/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
    shutil.copyfile(__file__,d/'analyzer.py')
    print(json.dumps({k:result[k] for k in ('area_fsm','area_joint','delta_joint_from_253','warm_bounds','summaries')},indent=2))


if __name__=='__main__':main()
