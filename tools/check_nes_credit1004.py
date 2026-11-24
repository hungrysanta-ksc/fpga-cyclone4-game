"""Validate 912 SPI ordering, snapshot credit, pixels, deadlines and rejected receipts."""
import argparse
import json
import math
from pathlib import Path

from check_nes_overlap1002 import rows
from check_nes_output970 import counters
from check_nes_plan975 import read, sha
from nes_credit1004 import ledger, seal_credit
from test_nes_banks557 import MASTER


def lines(path):
    return [list(map(int,x.split())) for x in path.read_text().splitlines()]


def audit_bus(d, policy, jobs, events):
    by_id={j['index']:j for j in jobs}
    starts=lines(d/'starts.txt')
    initial=next(e for e in reversed(events) if e.get('opcode')=='0xe0' and e['clock']<=jobs[0]['issue'])
    b=bytes.fromhex(initial['reply'])
    assert int.from_bytes(b[3:5],'big')==int.from_bytes(b[5:7],'big')==jobs[0]['index']-1
    assert len(starts)==20 and set(r[0] for r in starts)==set(by_id)-{jobs[0]['index']}
    e0=max(math.ceil(e['clock']-e['start']) for e in events if e.get('generation')==912 and e.get('opcode')=='0xe0')
    polls=lines(d/'status1004.txt')
    actions=[(t,t+e0,'poll',(sent,known,retired)) for t,sent,known,retired in polls]
    actions.extend((issue-query,end,'issue',(i,issue,used,query,avail))
                   for i,issue,end,used,query,avail in starts)
    busy=lines(d/'busy.txt')
    sent=jobs[0]['index']
    confirmed=sent-1
    tiles=0
    tail={}
    detail={}
    last=0
    returns=dict(lines(d/'returns970.txt'))
    positions={}
    quiet=0
    for start,end,kind,args in sorted(actions):
        assert start>=last and all(end<=a or start>=b for a,b in busy)
        last=end
        if kind=='poll':
            a,known,retired=args
            assert a==sent and known==confirmed and known<=retired<=a
            quiet+=known==retired
            confirmed=retired
            continue
        i,issue,used,query,avail=args
        j=by_id[i]
        assert avail==2-(sent-confirmed) and 1<=avail<=2 and 0<=used<=2-avail
        assert end-issue==j['duration'] and query==j.get('e8_cost',0)
        if policy in ('tile','both','feed') and (2 if policy=='feed' else 3)<=tiles<8 and j['op']!=7:
            assert avail==2
        if policy in ('seal','both') and sent==jobs[-1]['index']-2:
            assert avail==2
        section='tile' if 'token' in j else j['section']
        assert i>positions.get(section,0)
        positions[section]=i
        if 'token' in j:
            token=j['token']
            assert start>=j['producer']
            if token>=33:
                assert start>=returns[token-2]+j['fill_after_previous_return']
            tiles+=1
            if tiles>=4:
                tail[j['token']]=dict(issue=issue,arrive=end)
        if j['op']==3:
            assert i==jobs[-1]['index'] and sent==i-1
        detail[i]=dict(sequence=sent+1,available=avail,issue=issue,arrive=end)
        sent+=1
    assert tiles==8 and list(tail)==list(range(34,39))
    if policy in ('seal','both'):
        assert starts[-2][-1]==2 and starts[-1][-1]==1
        assert not any(starts[-2][2]<=p[0]<starts[-1][1] for p in polls)
    return dict(tail=tail,packets=detail,E0=len(polls),quiet_E0=quiet,E0_duration=e0)


def inspect(temp,phase):
    ref,_,jobs,events=ledger(temp,phase)
    old,new=seal_credit(events,jobs)
    previous=read(Path(__file__).resolve().parents[1]/'analysis/overlap1002-results.json')[str(phase)]
    start=previous['vblank46_start']
    cutoff=previous['line246_end']
    base=previous['baseline']
    prefix=[r for r in rows(ref/'window.csv') if int(r['g'])<912]
    assert counters(ref,908)['reveal']==previous['protected']['reveal908']
    assert sum(int(r['value']) for r in prefix if (r['g'],r['op'],r['event'])==('909','-1','ppu_dma'))==624
    assert max(e['clock'] for e in events if e.get('input_generation')==910 and e.get('opcode')=='0xd2')==previous['protected']['D2_910']
    runs={}
    for name in ('fixed','control','tile','seal','both','feed'):
        d=temp/f'nes-credit1004-{name}-p{phase}'
        win=rows(d/'window.csv')
        assert [r for r in win if int(r['g'])<912 and r['event']!='group1002']==prefix
        result=read(d/'result.json')
        assert result['passed'] and (result['commits'],result['last_status'])==(8,1)
        for g in range(905,913):
            assert sha(d/f'frame-{g}.rgb')==sha(ref/f'frame-{g}.rgb')
        clocks=counters(d,912)
        group,=[int(r['clock']) for r in win if (r['g'],r['op'],r['event'])==('912','3','group1002')]
        runs[name]=item=dict(group=group,group_late_ms=round((group-start)*1000/MASTER,6),
                              reveal=clocks['reveal'],seal=clocks['seal'],ack=clocks['ack'],
                              ack_delta=clocks['ack'][0]-base['ack'][0],
                              passed_target=(group<start and clocks['reveal'][0]<=cutoff and clocks['ack'][0]<base['ack'][0]))
        if name=='fixed':
            expected=math.ceil(new['clock'])+jobs[-1]['duration']
            assert result['frames'][-1]['release_masterclock']==expected
            item['seal_E1_end']=expected
        else:
            item.update(audit_bus(d,name,jobs,events))
            for tok,metrics in item['tail'].items():
                matches=[r for r in win if r['g']=='912' and r['event']=='consume920' and int(r['value'])==tok]
                row,=matches
                metrics['return']=int(row['clock'])
                metrics['load']=next(int(r['clock']) for r in win if r['index']==row['index'] and r['event']=='load')
    guards={}
    for name in ('tile','seal','feed'):
        for fault,status in [('bad_seal',224),('stop_decode',228)]:
            d=temp/f'nes-credit1004-{name}-p{phase}-{fault}'
            result=read(d/'result.json')
            assert result['passed'] and (result['commits'],result['last_status'])==(7,status)
            assert sha(d/'retained.rgb')==sha(ref/'frame-911.rgb')
            win=rows(d/'window.csv')
            assert not any(int(r['g'])>=912 and r['event']=='reveal' for r in win)
            assert any(r['event']=='ack' and int(r['value'])==status and r['op']=='3' for r in win)
            guards[f'{name}-{fault}']=status
    return dict(vblank46=start,cutoff=cutoff,base=base,protected=previous['protected'],
                credit_before_table=old,credit_before_seal=new,
                post_status_to_E1_clocks=jobs[-1]['issue']-math.ceil(new['clock']),runs=runs,guards=guards)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('output',type=Path)
    a=parser.parse_args()
    result={p:inspect(a.temp,p) for p in (1,2)}
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
