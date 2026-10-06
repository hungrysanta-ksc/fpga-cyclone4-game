# Independent reuse-distance and corruption tests. SPDX-License-Identifier: MIT.
from pathlib import Path
from itertools import product
from copy import deepcopy
import argparse, json, hashlib
from analyze_nes_fetch_workload import demand, max_window, events, replay
from verify_nes_mmc3_integrated import numbers

def fail(fn):
    try:
        fn()
    except AssertionError:
        return True
    return False

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    cases=0
    # LRU misses derived independently from distinct keys since last reference.
    for length in range(1,8):
        for keys in product(range(3),repeat=length):
            seq=[dict(tile=k,tick=i,frame=1,line=0) for i,k in enumerate(keys)]
            for capacity in (1,2,3):
                expected=[]
                for i,key in enumerate(keys):
                    prior=[j for j in range(i) if keys[j]==key]
                    if not prior or len(set(keys[prior[-1]+1:i]))>=capacity:
                        expected.append(i)
                assert [m['index'] for m in demand(seq,capacity)[0]]==expected
                cases+=1
    boundary=[dict(tick=t) for t in (0,31,32,1363,1364,1365,2728)]
    for width in (1,32,1364,10912):
        expected=max(sum(r['tick']-width<m['tick']<=r['tick'] for m in boundary) for r in boundary)
        assert max_window(boundary,width)['requests']==expected
    assert max_window([],32)['bytes']==0
    chrdata=bytes(int(v,16) for v in (a.run/'chr.hex').read_text().split())
    raw=numbers(a.run/'fetch.tsv')
    trace=events(raw,chrdata)
    totals={128:[958]*4,256:[256]*4,512:[256,256,0,0],1024:[256,256,0,0]}
    prefix_checks=0
    for cap,counts in totals.items():
        misses,_=demand(trace,cap)
        assert [sum(m['frame']==f for m in misses) for f in range(1,5)]==counts
        for end in (1,16388,16389,32776,49164):
            # Running only a prefix must produce byte-for-byte identical requests.
            assert demand(trace[:end],cap)[0]==[m for m in misses if m['index']<end]
            prefix_checks+=1
        decoded=replay(trace,misses,chrdata,cap)
        for f,data in decoded.items():
            expected=bytes(int(v,16) for v in (a.run/f'frame-{f:3}.hex').read_text().split())
            assert data==expected
    misses=demand(trace,512)[0]
    negative={}
    negative['missing_request']=fail(lambda:replay(trace,misses[1:],chrdata,512))
    for field,value in (('tick',misses[0]['tick']-1),('tile',misses[0]['tile']^512),('evicted',999)):
        changed=deepcopy(misses);changed[0][field]=value
        negative[field+'_corruption']=fail(lambda:replay(trace,changed,chrdata,512))
    changed=deepcopy(misses);changed.append(dict(changed[0],index=-1))
    negative['out_of_range_request']=fail(lambda:replay(trace,changed,chrdata,512))
    damaged=bytearray(chrdata);damaged[trace[0]['offset']]^=1
    negative['payload_corruption']=fail(lambda:replay(trace,misses,bytes(damaged),512))
    seq=trace.copy()
    index=next(i for i,e in enumerate(seq) if e['pixel'] is not None)
    seq.pop(index)
    negative['missing_pixel_plane']=fail(lambda:replay(seq,demand(seq,512)[0],chrdata,512))
    changed=raw.copy();r=list(changed[1]);r[3]=changed[0][3];changed[1]=tuple(r)
    negative['duplicate_tick']=fail(lambda:events(changed,chrdata))
    changed=raw.copy();r=list(changed[0]);r[5]^=8192;changed[0]=tuple(r)
    negative['physical_bank_corruption']=fail(lambda:events(changed,chrdata))
    assert all(negative.values()),negative
    result=dict(passed=True,reuse_distance_cases=cases,rolling_boundary_cases=5,
                actual_prefix_checks=prefix_checks,actual_replay_pixels=4*245760,
                capacities_tiles=list(totals),negative_tests=negative,
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                limitation='Software analysis correctness and ideal byte replay only; no transport deadline or SNES execution.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    main()