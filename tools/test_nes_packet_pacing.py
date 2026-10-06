# Independent tick-by-tick ownership oracle. SPDX-License-Identifier: MIT.
from pathlib import Path
from fractions import Fraction
import argparse,hashlib,json,random
from nes_packet_pacing import schedule
def brute(a):
    n=a['frames'];src=[0];dst=[0]
    for i in range(n):
        src.append(src[-1]+a['source_periods'][i%len(a['source_periods'])])
    for i in range(n+a['lag']):
        dst.append(dst[-1]+a['consumer_periods'][i%len(a['consumer_periods'])])
    def ceil_fraction(x):return -(-x.numerator//x.denominator)
    release=[a['phase']+ceil_fraction(Fraction((t+a['release_offset'])*1000000,1000000+a['ppm'])) for t in src[:-1]]
    deadlines=[dst[i+a['lag']+1]-a['guard'] for i in range(n)]
    owned=set();items={};link=None;next_send=0;next_consume=0;endings={};peak=0
    until=max(deadlines+release)+100
    for t in range(until+1):
        for i in list(owned):
            if endings.get(i)==t:owned.remove(i)
        failures=[]
        for i,r in enumerate(release):
            if r==t:
                owned.add(i);items[i]={'encoded':t+a['encode_ticks']}
                peak=max(peak,len(owned))
                if len(owned)>a['slots']:failures.append(dict(kind='overflow',time=t,frame=i+1))
        if link is not None and link[1]==t:
            items[link[0]]['ready']=t+a['cdc_ticks'];link=None
        if link is None and next_send in items and items[next_send]['encoded']<=t:
            size=a['packet_sizes'][next_send%len(a['packet_sizes'])]
            link=(next_send,t+size*a['clocks_per_byte']);next_send+=1
        if next_consume in items and next_consume<n:
            i=next_consume
            if (items[i].get('ready',until+1)<=t and t>=dst[i+a['lag']]+a['blank_offset']+a['poll']
                    and (i==0 or endings[i-1]<=t)):
                endings[i]=t+a['duration'];next_consume+=1
        for i,d in enumerate(deadlines):
            if d==t and endings.get(i,t+1)>t:
                failures.append(dict(kind='deadline',time=t,frame=i+1))
        if failures:return dict(first=min(failures,key=lambda v:(v['time'],v['frame'],v['kind'])),peak=peak)
        if len(endings)==n and not owned:return dict(first=None,peak=peak)
    raise AssertionError('oracle horizon')
def test():
    rng=random.Random(26005);cases=0
    for _ in range(300):
        a=dict(frames=5,source_periods=(36,40),consumer_periods=(40,36),release_offset=25,
               packet_sizes=(1,2,3),duration=rng.randint(1,7),blank_offset=30,guard=1,poll=rng.randint(0,2),
               phase=rng.randint(0,39),lag=rng.randint(0,2),encode_ticks=rng.randint(0,4),
               clocks_per_byte=rng.randint(1,3),cdc_ticks=rng.randint(0,2),
               ppm=rng.choice((-100000,0,100000)),slots=rng.randint(1,3))
        result=schedule(**a);oracle=brute(a)
        got=result['first_violation']
        actual=None if got is None else {k:got[k] for k in ('kind','time','frame')}
        assert actual==oracle['first'],(a,actual,oracle)
        assert result['peak_owned_slots_through_first_violation']==oracle['peak'],(a,result,oracle)
        cases+=1
    checks={}
    r=schedule(frames=4,encode_ticks=2924)
    checks['exact_short_deadline_pass']=r['pass_without_drop_repeat_or_stall'] and r['first_frames'][0]['margin']==0
    r=schedule(frames=4,encode_ticks=2925)
    checks['one_tick_late_fail']=r['first_violation']==dict(kind='deadline',time=357360,frame=1,late_ticks=1)
    r=schedule(frames=16,lag=1,slots=1)
    checks['one_slot_overlap_detected']=r['first_violation']['kind']=='overflow'
    checks['two_slot_nominal_pass']=schedule(frames=60000,lag=1)['pass_without_drop_repeat_or_stall']
    checks['faster_eventually_overflows']=schedule(frames=12000,lag=1,ppm=100)['first_violation']['kind']=='overflow'
    checks['slower_eventually_misses']=schedule(frames=12000,lag=1,ppm=-100)['first_violation']['kind']=='deadline'
    try:schedule(frames=1,slot_bytes=2048)
    except AssertionError:checks['2KiB_cannot_hold2328']=True
    else:checks['2KiB_cannot_hold2328']=False
    checks['half_phase_one_lag_pass']=schedule(frames=16,phase=178684,lag=1)['pass_without_drop_repeat_or_stall']
    checks['last_phase_one_lag_pass']=schedule(frames=16,phase=357363,lag=1)['pass_without_drop_repeat_or_stall']
    checks['phase1900_same_frame_pass']=schedule(frames=16,phase=1900,lag=0)['pass_without_drop_repeat_or_stall']
    checks['phase1901_same_frame_fails']=not schedule(frames=16,phase=1901,lag=0)['pass_without_drop_repeat_or_stall']
    checks['last_phase_two_lag_pass']=schedule(frames=16,phase=357363,lag=2,slots=3)['pass_without_drop_repeat_or_stall']
    # A slot cannot be freed at consumer start; current frame still reads it during DMA.
    r=schedule(frames=16,lag=1)
    checks['release_after_commit_only']=r['peak_owned_slots_through_first_violation']==2
    assert all(checks.values()),checks
    return dict(passed=True,independent_tick_oracle_cases=cases,boundary_and_regression_tests=checks,
                test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    r=test();a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r,indent=2))
