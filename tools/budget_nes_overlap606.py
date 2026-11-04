"""Compare capture-time CHR retention with a charged, previous-ACK-first input schedule."""
import argparse
import bisect
import json
from pathlib import Path
from statistics import median

from analyze_nes_wire600 import MASTER, ms
from check_nes_wire600 import ROOT, read, pin

G=954
RATE=MASTER/1000
CAPTURE=240*341*4


def material(a):
    fixture=a.stim601/'stim.tsv'
    pin(fixture,read(ROOT/'analysis/snoop601-verification.json')['fixture_sha256'])
    stim=read(ROOT/'analysis/geometry230-verification.json')['stimulus_result_sha256']
    pin(a.geometry/'result.json',stim)
    files=read(a.geometry/'result.json')['frames']
    supplied={};demand={};g=904
    for f in (954,955):
        path=a.geometry/f'frame{f}.hex';pin(path,next(r for r in files if r['frame']==f)['stimulus_sha256'])
        observations=[]
        for t,line in enumerate(path.read_bytes().splitlines()):
            w=int(line,16)
            if (w>>54)&3==3:
                plane=w>>49&15;assert plane in (1,2,4,8)
                observations.append((t,int(plane>2),w&131071))
        supplied[f]=observations
        demand[f]=[]
    writes={954:[],955:[]}
    with fixture.open() as stream:
        for line in stream:
            op,k,adr,v,_=line.split()
            if op=='0':g+=1
            elif g in writes:
                row=(int(k),int(adr,16),int(v,16))
                (writes if op=='1' else demand)[g].append(row)
    for f in writes:
        assert [(k,a) for t,k,a in supplied[f]]==[(k,a) for k,a,v in writes[f]]
        supplied[f]=[(t,k,a,v) for (t,k,a),(_,_,v) in zip(supplied[f],writes[f],strict=True)]
    assert len(set(demand[G]))==len(demand[G])==272
    return supplied,demand[G]


class Cache:
    def __init__(self,n):
        self.n=n;self.lines={}

    def write(self,k,a,v):
        tag=a//16;key=(k,tag%self.n)
        if key not in self.lines or self.lines[key][0]!=tag:self.lines[key]=(tag,{})
        self.lines[key][1][a%16]=v

    def hit(self,k,a,v):
        tag=a//16
        old=self.lines.get((k,tag%self.n))
        if old is None or old[0]!=tag or a%16 not in old[1]:return False
        assert old[1][a%16]==v
        return True


def retention(samples,demand,n):
    cache=Cache(n)
    # Only potentially affected demand keys need to be rechecked after each write.
    lines={}
    for row in demand:lines.setdefault((row[0],row[1]//16%n),[]).append(row)
    present=set();first={};last_below={};cross={}
    for t,k,a,v in samples:
        cache.write(k,a,v)
        for row in lines.get((k,a//16%n),[]):
            if cache.hit(*row):present.add(row);first.setdefault(row,t+1)
            else:present.discard(row)
        for target in (264,272):
            if len(present)<target:last_below[target]=True
            elif last_below.pop(target,False):cross[target]=t+1
    return dict(lines_per_kind=n,data_B=n*32,ever_seen_B=len(first),sealed_B=len(present),
                stable_dot={str(b):cross[b] for b in (264,272) if len(present)>=b},
                first_seen_264_dot=sorted(first.values())[263] if len(first)>=264 else None)


def phase_budget(ph,io,prefix,supplied,demand,n):
    folder=ph['folder'];clock=ph['origin']
    events=read(folder/'events.json')
    prev=[e for e in events if e['generation']==G-1]
    seal=next(e['clock'] for e in prev if e.get('packet_opcode')==3 and e.get('opcode')=='0xe1')
    polls=[e for e in prev if e.get('opcode')=='0xe0' and e['start']>seal]
    assert all(e['reply']==polls[0]['reply'] for e in polls[:-1])
    assert polls[-1]['reply']!=polls[0]['reply'] and polls[-2]['start']<ph['ack']<=polls[-1]['start']
    assert not any(e.get('event')=='observer' and e['clock']>polls[0]['start'] for e in prev)
    assert prev[-1]['opcode']=='0xea' and prev[-1]['clock']==clock
    free=[(b['start']-a['clock'])/RATE for a,b in zip(polls,polls[1:])]
    period=median((b['start']-a['start'])/RATE for a,b in zip(polls,polls[1:]))
    def rel(t):return (t-clock)/RATE
    cap0=ph['ready']-CAPTURE
    after=next(e for e in events if e['generation']==G+1 and e['event']=='source_begin')
    cap1=after['capture_ready']-CAPTURE
    # At the original addresses and request times, compare one retained, writable cache
    # with the mutually-exclusive sample/query port contract in RTL601.
    service=read(folder/'obj-phases.json')[str(G)]['rom_service']
    assert len(service)==len(demand)
    cache=Cache(n)
    for _,k,a,v in supplied[G]:cache.write(k,a,v)
    i=0;hits=0;blocked=0;legal=0
    for (kind,req,grant,rsp),row in zip(service,demand,strict=True):
        assert kind==row[0] and ph['ready']<=req<=grant<rsp
        while i<len(supplied[G+1]) and cap1+4*(supplied[G+1][i][0]+1)<=req:
            _,k,a,v=supplied[G+1][i];cache.write(k,a,v);i+=1
        busy=cap1<=req<after['capture_ready']
        ok=cache.hit(*row);hits+=ok;blocked+=busy;legal+=ok and not busy
    terminal=next(r for r in reversed(prefix) if r['token']==len(prefix)-1)['confirmed_ms']
    e9=next(e for e in io if e['op']=='0xe9')
    seal_new=next(e['end'] for e in io if e.get('packet')==3)
    remaining=sum(e['n'] for e in io if e['op'] in ('0xe1','0xe9') and e['start']>=e9['end'] and e['end']<=seal_new)
    # Check exactly why the 604 output model sends more than the coupled 561 run.
    def ledger(out):
        totals={}
        for op,section,size in out:totals[op,section]=totals.get((op,section),0)+size
        return totals
    current=ledger((e['packet'],e['section'],e['n']) for e in io if e['op']=='0xe1')
    frozen=[]
    for line in (folder/'packets.jsonl').read_text().splitlines():
        _,_,h,_=json.loads(line);b=bytes.fromhex(h)
        if int.from_bytes(b[8:10],'little')==G:frozen.append((b[0],b[1],len(b)+3))
    old=ledger(frozen)
    assert set(old)==set(current)
    diff={k:current[k]-old[k] for k in old if current[k]!=old[k]}
    assert set(diff)=={(7,0),(7,1)}
    saved=sum(diff.values());assert saved==437
    assert all(e['start']>=e9['end'] for e in io if e.get('packet')==7 or e.get('section')==2)
    recipe=read(ROOT/'analysis/abi582-verification.json')['frames'][G-905]['map']
    compact=recipe['wire_B']
    assert current[2,2]==2148 and compact==622
    initial_io=sum(e['end']-e['start'] for e in io if e['start']>=terminal and e['end']<=e9['end'])
    deadline=rel(ph['reveal']+MASTER/60)
    post= e9['end']-terminal+ms(remaining)
    tail=[e for e in io if e['start']>=e9['end']]
    nbulk=sum(op==7 for op,_,_ in frozen)
    e1_calls=sum(e['op']=='0xe1' for e in tail)-sum(e.get('packet')==7 or e.get('section')==2 for e in tail)+nbulk+recipe['packets']
    e9_calls=sum(e['op']=='0xe9' for e in tail)
    driver=(e1_calls*ph['driver']['0xe1']+e9_calls*ph['driver']['0xe9'])/1000
    allfree=max((b for b in prefix if b['confirmed_ms']<=-rel(seal)),key=lambda b:b['token'])
    # Admit exactly the six tentative blocks through the first validated BG-tag
    # prefix from 605. Each full old negative-poll service period is charged.
    # Rejoin the old poll grid after each block; no choice uses the future ACK.
    starts=[rel(e['start']) for e in polls];index=0;skipped=0;worst=0;end=0
    for j in range(6):
        assert index<len(polls)-1
        duration=prefix[j]['confirmed_ms']-(prefix[j-1]['confirmed_ms'] if j else 0)
        done=starts[index]+period+duration
        following=bisect.bisect_left(starts,done)
        assert following<len(polls) and starts[index]<rel(ph['ack'])
        skipped+=following-index-1;worst=max(worst,starts[following]-starts[index])
        index=following;end=done
    assert index<len(polls)-1 and end<rel(ph['reveal'])
    moved=prefix[5]['confirmed_ms']
    return dict(phase=ph['phase'],capture_start_vs_source_ms=rel(cap0),capture_ready_vs_source_ms=rel(ph['ready']),
                prior_seal_ms=rel(seal),prior_reveal_ms=rel(ph['reveal']),prior_ACK_ms=rel(ph['ack']),
                deadline_ms=deadline,next_capture_start_ms=rel(cap1),next_capture_end_ms=rel(after['capture_ready']),
                observed_954_queries_during_955_capture=blocked,rolling_cache_hits=hits,
                original_port_permitted_hits=legal,negative_E0s=len(polls)-1,poll_period_ms=period,
                max_idle_between_polls_ms=max(free),first_D1_ms=next(e['end']-e['start'] for e in io if e['op']=='0xd1'),
                six_block_ms=moved,six_block_last_ms=end,skipped_negative_E0=skipped,
                poll_gap_with_overlap_ms=worst,first_positive_and_EA_shift_ms=0,
                after_EA_commit_ms=terminal-moved,first_E9_after_overlap_ms=e9['end']-moved,
                modeled_SEAL_after_overlap_ms=seal_new-moved,
                post_E9_mandatory_wire_B=remaining,conditional_SEAL_floor_after_overlap_ms=e9['end']-moved+ms(remaining),
                commit_to_E9_nontransfer_ms=e9['end']-terminal-initial_io,commit_to_E9_transfer_ms=initial_io,
                observed_bulk_saving_B=saved,modeled_map_saving_B=current[2,2]-compact,
                ideal_input_hidden_batched_floor_ms=post-ms(saved),
                ideal_input_hidden_batched_compact_floor_ms=post-ms(saved+current[2,2]-compact),
                ideal_batched_compact_plus_mean_driver_ms=post-ms(saved+current[2,2]-compact)+driver,
                tail_batched_compact_calls=dict(E1=e1_calls,E9=e9_calls),
                ideal_post_SEAL_blocks=allfree['token']+1,ideal_post_SEAL_geometry_counts=allfree['at'],
                ideal_all_input_hidden_floor_ms=post,ideal_all_input_hidden_late_ms=post-deadline,
                ideal_all_input_hidden_excess_wire_equivalent_B=(post-deadline)/ms(1))


def main(a):
    supplied,demand=material(a)
    ret=[retention(supplied[G],demand,n) for n in (16,32,64,128)]
    target=next(r for r in ret if r['sealed_B']>=264)
    old=read(ROOT/'analysis/wire600-verification.json')
    whole=read(ROOT/'analysis/whole580-verification.json')
    src=read(ROOT/'analysis/overlap606-trace.json')['frames'][0]
    prefix=next(r for r in read(ROOT/'analysis/prefix605-trace.json')['frames'] if r['generation']==G)['prefix']
    phases=[]
    for ph in whole['phases']:
        folder=a.traces/f"nes-close561-run{ph['phase']}"
        for f in ('events.json','obj-phases.json','window.csv','packets.jsonl'):pin(folder/f,ph['evidence'][f])
        prior=next(r['relaxed_calendar'] for r in old['phases'] if r['generation']==G and r['phase']==ph['phase'])
        source=next(e for e in read(folder/'events.json') if e['generation']==G and e['event']=='source_begin')
        assert source['clock']==prior['source_begin'] and source['capture_ready']<source['clock']
        p=dict(folder=folder,origin=source['clock'],ready=source['capture_ready'],reveal=prior['previous_reveal'],
               ack=prior['previous_ACK'],phase=ph['phase'],driver=ph['parameters']['driver_extra_us'])
        row=phase_budget(p,src['io'],prefix,supplied,demand,target['lines_per_kind'])
        row['stable_264_vs_source_ms']=row['capture_start_vs_source_ms']+target['stable_dot']['264']*4/RATE
        phases.append(row)
    result=dict(stage=606,physical_baseline='MMC577',generation=G,retention=ret,phases=phases,
                scope='Capture dots anchored to the 561 capture gate. 604 trace after EA uses modeled consumer. Protected overlap replay, no new board STA or final ACK.',
                measured_board_FIT=None,new_display_interval=None)
    a.report.write_bytes((json.dumps(result,indent=2)+'\n').encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('geometry','stim601','traces','report'):p.add_argument('--'+arg,required=True,type=Path)
    main(p.parse_args())
