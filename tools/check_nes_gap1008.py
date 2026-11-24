"""Check token 36, paid wire/credit, independent receipts and the 246-line budget."""
import argparse
import json
import math
from pathlib import Path

from check_nes_credit1004 import lines
from check_nes_output970 import counters
from check_nes_plan975 import read, sha
from check_nes_blank959 import rows
from nes_gap1008 import POLICIES, fixed_window, ledger


def fixed_report(temp,phase,policy,ref,jobs,events):
    """Audit snapshot credit and tile readiness again with the replayed retire times."""
    out=temp/f'nes-gap1008-fixed-{policy}-p{phase}'
    run=read(out/'result.json')
    assert run['passed'] and (run['commits'],run['last_status'])==(8,1)
    for g in range(905,913):
        assert sha(out/f'frame-{g}.rgb')==sha(ref/f'frame-{g}.rgb')
    win=rows(out/'window.csv')
    base=rows(ref/'window.csv')
    assert [r for r in win if int(r['clock'])<=jobs[8]['arrive'] and r['event']!='group1002']==[
        r for r in base if int(r['clock'])<=jobs[8]['arrive']]
    head=jobs[8]
    order=list(range(len(jobs)))
    start,early_issue=fixed_window(policy,jobs,events) if policy!='hold' else (0,0)
    blocked=[]
    if policy!='hold':
        idx=next(i for i,j in enumerate(jobs) if j['index']==POLICIES[policy])
        order.remove(idx)
        order.insert(9,idx)
        end=early_issue+jobs[idx]['duration']
        blocked=[e for e in events if 'start' in e and e['start']<end and e['clock']>start]
        assert blocked and all(e.get('opcode')=='0xe0' for e in blocked)
    polls=[e for e in events if e.get('opcode')=='0xe0' and e not in blocked]
    ack=[(int(r['index']),int(r['clock'])) for r in win if r['event']=='ack']
    ret=dict(lines(out/'returns970.txt'))
    ready_slack=[]
    outstanding=[]
    for i in range(9,len(order)):
        j=jobs[order[i]]
        issue=early_issue if policy!='hold' and i==9 else j['issue']
        sample=next(e for e in reversed(polls) if e['clock']<=issue)
        # Conservatively allow a further 256 master clocks for physical ACK
        # publication. The calculation tests capacity, not ARM status identity.
        confirmed=max(n for n,clock in ack if clock+256<sample['start'])
        outstanding.append(jobs[0]['index']+i-1-confirmed)
        if 'token' in j:
            tok=j['token']
            sample_time=start if policy=='next_obj' and tok==37 else j['e8_start']
            ready_slack.append(sample_time-max(j['producer'],ret[tok-1],ret[tok-2]+j['fill_after_previous_return']))
    schedule=counters(out,912)
    if policy=='hold':
        assert schedule==counters(ref,912)
    received=next(int(r['clock']) for r in win if r['g']=='912' and r['index']=='183' and r['event']=='ack')
    return dict(E8_37_sample=start if policy=='next_obj' else jobs[9]['e8_start'],credit_used_before_issue=outstanding, min_E8_margin=min(ready_slack),
                overwritten_E0=len(blocked),token36_return=ret[36],token36_ack=received,
                eligible_4credit=max(outstanding)<4 and min(ready_slack)>=0,
                early46=sum(int(r['value']) for r in win if (r['g'],r['frame'],r['event'],r['op'])==('912','46','ppu_dma','-1')),
                first_tail_ack=next(int(r['clock']) for r in win if r['event']=='ack' and r['index']=='184'),
                schedule=schedule,ack_delta=schedule['ack'][0]-counters(ref,912)['ack'][0])


def inspect(temp,phase):
    ref,_,jobs,events=ledger(temp,phase)
    by_id={j['index']:j for j in jobs}
    src=Path(__file__).resolve().parents[1]/'analysis/overlap1002-results.json'
    limits=read(src)[str(phase)]
    begin,limit=limits['vblank46_start'],limits['line246_end']
    baseline=rows(ref/'window.csv')
    seal0=counters(ref,912)
    e0=max(math.ceil(e['clock']-e['start']) for e in events if e.get('opcode')=='0xe0' and e['generation']==912)
    gate=jobs[9]['e8_start']
    packet36=jobs[8]
    assert packet36['token']==36
    def prefix(win):
        return [r for r in win if int(r['clock'])<=packet36['arrive'] and r['event']!='group1002']
    def dma(win):
        return [[int(r[k]) for k in ('clock','frame','line','value','op')] for r in win
                if r['g']=='912' and r['event']=='ppu_dma']
    stock=dma(baseline)
    tail=[r[3] for r in stock if r[-1]==3]
    last_prefetch=max(int(r['clock']) for r in baseline if (r['g'],r['op'],r['event'])==('912','-1','ppu_last'))
    assert tail[-2:]==[512,544] and sum(r[3] for r in stock if r[-1]==-1)==496
    result=dict(vblank_start=begin,cutoff=limit,original=seal0,original_dma=stock,head_return=packet36['physical_return'],
                head_ack=packet36['ack'],original_E8_37=gate,last_prefetch_end=last_prefetch,
                remaining_clocks=limit-last_prefetch,remaining_DMA_B=sum(tail),minimum_DMA_clocks=8*sum(tail),
                palette_OAM_only_clocks=8*sum(tail[-2:]),runs={})
    instrumented = ref.with_name(ref.name.replace('978returned','1008drain'))
    matched = ['events.json','producer.jsonl','window.csv','records.bin','client.sfc']
    assert instrumented != ref and all(sha(ref/n)==sha(instrumented/n) for n in matched)
    calls = read(temp/f'nes-drain1008-p{phase}.json')
    polls = [e for e in events if e.get('opcode')=='0xe0' and packet36['arrive']<=e['start']<gate]
    receipt = next(e for e in polls if int.from_bytes(bytes.fromhex(e['reply'])[5:7],'big')==packet36['index'])
    following = [e for e in polls if e['start']>=receipt['clock']]
    callers = [r for r in calls if receipt['clock']<=r[0]<gate]
    assert len(following)==len(callers)==12 and all(e['reply']==receipt['reply'] for e in following)
    assert all(r[1:] == ['nes_plan200_progress',328] and 0<e['start']-r[0]<150 for r,e in zip(callers,following,strict=True))
    result['ARM_polling'] = dict(matched_files=matched,receipt_end=receipt['clock'],E8_start=gate,
        unchanged_replies=len(following),caller=callers[0][1:],clocks_after_receipt=gate-receipt['clock'])
    result['palette_OAM_shortfall']=result['palette_OAM_only_clocks']-result['remaining_clocks']
    result['all_DMA_shortfall']=result['minimum_DMA_clocks']-result['remaining_clocks']
    for policy in POLICIES:
        out=temp/f'nes-gap1008-{policy}-p{phase}'
        run=read(out/'result.json')
        win=rows(out/'window.csv')
        assert run['passed'] and (run['commits'],run['last_status'])==(8,1)
        assert prefix(win)==prefix(baseline)
        for g in range(905,913):
            assert sha(out/f'frame-{g}.rgb')==sha(ref/f'frame-{g}.rgb')
        tokens=dict(lines(out/'returns970.txt'))
        assert list(sorted(tokens))[-8:]==list(range(31,39))
        starts=lines(out/'starts.txt')
        assert sorted(r[0] for r in starts)==list(range(184,196))
        busy=lines(out/'busy.txt')
        polls=lines(out/'status1004.txt')
        actions=[(t,t+e0,0,(sent,known,retired)) for t,sent,known,retired in polls]
        actions.extend((issue-query,end,1,(idx,issue,query,available)) for idx,issue,end,_,query,available in starts)
        last=packet36['arrive']
        n,confirmed=183,182
        before=[]
        positions={}
        for at,end,kind,params in sorted(actions):
            assert at>=last and all(end<=a or at>=b for a,b in busy)
            last=end
            if kind==0:
                sent,known,retired=params
                assert sent==n and known==confirmed and confirmed<=retired<=n
                confirmed=retired
                continue
            idx,issue,query,available=params
            job=by_id[idx]
            assert available==2-(n-confirmed) and available>0
            assert end-issue==job['duration'] and query==job.get('e8_cost',0)
            section='tile' if 'token' in job else job['section']
            assert idx>positions.get(section,0)
            positions[section]=idx
            if 'token' in job:
                tok=job['token']
                earliest=0 if policy=='next_obj' and tok==37 else gate
                assert at>=max(earliest,job['producer'],tokens[tok-1],tokens[tok-2]+job['fill_after_previous_return'])
            else:
                assert at>=job.get('source',0)
                if 'assembled' in job and policy!='precopy':
                    assert at>=job['assembled']
            if at<gate:
                assert idx==POLICIES[policy] and end<=gate
                before.append(idx)
            n+=1
        assert n==195 and starts[-1][0]==195
        first_ack=next(int(r['clock']) for r in win if r['event']=='ack' and r['index']=='183')
        schedule=counters(out,912)
        stages={r['event']:int(r['clock']) for r in win if r['g']=='912' and r['op']=='3'
                and r['event'] in ('validate181','coverage212','upload165_entry','group1002','select169','reveal')}
        dm=dma(win)
        result['runs'][policy]=dict(before_E8_37=before,E0=len(polls),packets=starts,
            token36_return=tokens[36],token36_ack=first_ack,all_preseal_DMA_B=sum(r[3] for r in dm if r[-1]==-1),
            DMA_in_VB46=sum(r[3] for r in dm if r[1]==46 and r[-1]==-1),
            group_late=stages['group1002']-begin,stages=stages,dma=dm,schedule=schedule,
            ACK_delta=schedule['ack'][0]-seal0['ack'][0])
    result['fixed']={policy:fixed_report(temp,phase,policy,ref,jobs,events)
                     for policy in ('hold','palette','oam','precopy','next_obj')}
    assert all(v['eligible_4credit'] for v in result['fixed'].values())
    result['guards']={}
    for fault,status in (('bad_seal',224),('stop_decode',228)):
        out=temp/f'nes-gap1008-fixed-palette-p{phase}-{fault}'
        run=read(out/'result.json')
        assert run['passed'] and (run['commits'],run['last_status'])==(7,status)
        assert sha(out/'retained.rgb')==sha(ref/'frame-911.rgb')
        result['guards'][fault]=status
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    result={phase:inspect(a.temp,phase) for phase in (1,2)}
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
