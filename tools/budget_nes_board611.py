"""Verify actual 610 binaries, preserved BG hits and whole-board 611 evidence."""
import argparse,csv,json,re
from bisect import bisect_right
from collections import Counter
from pathlib import Path
from statistics import median
from analyze_nes_phase537 import Calendar,ROOT,read,sha,ms,one,csv_groups
from analyze_nes_seal538 import inspect_run
from budget_nes_pace610 import removed_line_hits
from test_nes_obj609 import capture

def run(a,folder,base,reference):
    obj=read(folder/'obj-phases.json');cal=Calendar(a.calendar)
    fixture=capture(a.samples);tag=None;line={};counts=Counter();first={};reuse=[]
    events=read(folder/'events.json');cpu=csv_groups(folder/'window.csv')
    source={e['generation']:e for e in events if e['event']=='source_begin'}
    oldhits={(r['generation'],r['address']) for r in removed_line_hits(a.samples)['rows']}
    observed=set()
    for g in range(905,958):
        rows=obj[str(g)].get('cache611',[]);final=one([r for r in cpu[g] if r['op']==3],'ack')['clock']
        for kind,addr,t,grant,response,mode in rows:
            assert source[g]['capture_ready']<=t<response<=final
            if reference or kind==0:
                hit=tag==addr//16 and addr%16 in line
                if not hit:
                    if tag!=addr//16:tag=addr//16;line={}
                    line[addr%16]=True
                expected='BG_hit' if hit and kind==0 else 'OBJ_line_hit' if hit else 'ROM'
                delay=0 if reference else 1
            else:
                row=fixture[g].get((addr//16)%128)
                hit=row is not None and row[0]==addr//16 and addr%16 in row[1]
                expected='OBJ_capture' if hit else 'ROM';delay=8
            assert mode==expected
            assert (grant,response)==((t,t+(8 if mode=='OBJ_capture' else 1)) if hit else cal.select(t+delay))
            counts[mode]+=1
            if mode=='BG_hit':observed.add((g,addr))
            if kind==0 and g not in first:first[g]=(t,grant,response,mode)
        assert final<=obj[str(g)]['ea']
        if g+2 in source:reuse.append(source[g+2]['capture_ready']-240*341*4-obj[str(g)]['ea'])
    assert observed==oldhits and counts['BG_hit']==48 and min(reuse)>=0
    assert sum(counts.values())==5616 and counts['OBJ_capture']==(0 if reference else 1200)
    # Only reuse independently checked cache services. Hits are not ROM grants.
    services={v[0]:v[1:3] for v in first.values()}
    class Services:
        summary=cal.summary;period=cal.period;starts=cal.starts
        def select(self,t):return services[t] if t in services else cal.select(t)
    joint=read(folder/'joint.json')
    metric=inspect_run(folder,a.plans,Services(),base,a.firmware_sha,a.client_sha,
                       first_bg_limit=3,first_bg_requests={g:v[0] for g,v in first.items()})
    pushes=[json.loads(x)[1] for x in (folder/'packets.jsonl').read_text().splitlines()]
    retired=sorted(r['clock'] for rs in cpu.values() for r in rs if r['event']=='ack')
    occupancy=Counter()
    for e in events:
        if e.get('opcode')=='0xe0':
            b=bytes.fromhex(e['reply']);sent=int.from_bytes(b[3:5],'big');done=int.from_bytes(b[5:7],'big')
            assert (sent,done)==(bisect_right(pushes,e['start']),bisect_right(retired,e['start']))
            occupancy[sent-done]+=1
    assert max(occupancy)<=4 and joint['max_bulk_banks']==2
    watched={};displays=[]
    for g in range(905,958):
        seal=[r for r in cpu[g] if r['op']==3];rev=one(seal,'reveal');ack=one(seal,'ack')
        displays.append(rev['clock'])
        if g in (912,931,939,951,952,954,957):
            prev=one([r for r in cpu[g-1] if r['op']==3],'reveal');fin=one(seal,'final212')
            watched[g]=dict(interval_ms=ms(rev['clock']-prev['clock']),interval_VB=rev['frame']-prev['frame'],
                ACK=ack['clock'],final_waits=sum(r['event']=='wait169' and r['clock']>=fin['clock'] for r in seal),
                first_BG=first.get(g))
    intervals=sorted(ms(y-x) for x,y in zip(displays[1:],displays[2:]))
    metric.update(cache=counts,watched=watched,occupancy=occupancy,min_reuse_ms=ms(min(reuse)),
        after_first_two=dict(mean_ms=sum(intervals)/len(intervals),median_ms=median(intervals),p95_ms=intervals[-3],max_ms=max(intervals)))
    return metric

def timing(folder,name):
    p=folder/name
    with p.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    return dict(hash=sha(p),worst={k:min((r for r in rows if r['check']==k),key=lambda r:float(r['slack']))
                for k in ('setup','hold','recovery','removal')})

def fit(folder):
    p=folder/'output_files/board.fit.summary';s=p.read_text()
    def number(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s)[1].replace(',',''))
    rpt=(folder/'output_files/board.fit.rpt').read_text()
    m=re.search(r';\s*M9Ks\s*;\s*(\d+)\s*/',rpt)
    assert m
    return dict(LE=number('Total logic elements'),comb=number('Total combinational functions'),FF=number('Dedicated logic registers'),
        RAM_bits=number('Total memory bits'),M9K=int(m[1]),summary_sha=sha(p),report_sha=sha(folder/'output_files/board.fit.rpt'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','plans','calendar','samples','board','baseline','simulation','lifecycle','report'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=read(ROOT/'analysis/pace610-verification.json')
    for n,r in read(ROOT/'analysis/whole580-manifest.json')['FPGA_inputs'].items():assert sha(a.baseline/n)==r['sha256']
    inputs=read(a.board/'inputs611.json')
    for n,h in inputs.items():assert sha(a.board/n)==h
    sim=read(a.simulation/'result.json');life=read(a.lifecycle/'result.json')
    for n,h in sim['inputs'].items():assert inputs[n]==sha(a.simulation/n)==h
    for n,h in sim['benches'].items():assert sha(ROOT/'tools'/(n+'.sv'))==h
    for n,r in sim['logs'].items():assert sha(a.simulation/(n+'.log'))==r['sha256']
    for n,h in life['inputs'].items():assert inputs[n+'.sv']==h
    assert inputs['nes_live_joint.sv']==life['top']
    assert sha(a.lifecycle/'test.sv')==life['bench'] and sha(a.lifecycle/'vsim.log')==life['log']
    with (a.board/'second-paths611.tsv').open() as f:second=list(csv.DictReader(f,delimiter='\t'))
    assert len(second)==12 and all(float(r['slack'])>0 for r in second)
    a.firmware_sha=prior['phases'][0]['firmware'];a.client_sha=prior['phases'][0]['client']
    phases=[]
    for i in (1,2):
        ref=a.traces/f'nes-board611-ref{i}';candidate=a.traces/f'nes-board611-run{i}'
        old=run(a,ref,ref,True);new=run(a,candidate,ref,False)
        phases.append(dict(phase=i,reference=old,candidate=new,last_ACK_delta_ms=ms(new['last_ACK']-old['last_ACK']),
            delta_vs610_ms=ms(new['last_ACK']-prior['phases'][i-1]['last_ACK'])))
    report=dict(stage=611,phases=phases,board=fit(a.board),baseline=fit(a.baseline),
        raw_STA=timing(a.board,'raw-paths611.tsv'),reviewed_STA=timing(a.board,'paths611.tsv'),baseline_reviewed_STA=timing(a.baseline,'paths611.tsv'),
        inputs=read(a.board/'inputs611.json'),source_simulation=read(a.simulation/'result.json'),lifecycle=read(a.lifecycle/'result.json'),
        inherited_ARM_guards=prior['ARM_guards'],firmware_SHA=a.firmware_sha,client_SHA=a.client_sha,
        second_stage_STA=second,CDC_review_sha=sha(a.board/'cdc611.sdc'),
        baseline_CDC_note='The rearm registers are optimized/merged in the reference placement; exact rearm paths do not exist. Reference uses its original constraints; no ignored wildcard constraints.',
        scope='Actual linked ARM/65816 plus measured ROM calendar model; separate actual collector/lease/source RTL tests and whole-board FIT. Not full NES/PSRAM cosimulation or hardware FPS.',
        BG_hits_preserved=True,whole_FIT=True,selected_for_hardware=False,physical=False)
    report['schedule_gate']=all(q['candidate']['watched'][957]['final_waits']==0 and q['last_ACK_delta_ms']<0 and q['candidate']['dense_ms']<q['reference']['dense_ms'] for q in phases)
    report['STA_gate']=all(float(v['slack'])>=0 for v in report['reviewed_STA']['worst'].values())
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
