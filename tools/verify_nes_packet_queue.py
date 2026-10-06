# Reparse actual packet-queue RTL evidence. SPDX-License-Identifier: MIT.
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(run,repo):
    m=json.loads((run/'result.json').read_text());log=(run/'simulation.log').read_text()
    assert m['passed'] and all(v==0 for v in m['phases'].values())
    assert 'PASS NES PACKET QUEUE checks=14' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
    for name,h in m['output_hashes'].items():assert sha(run/name)==h
    for name,h in m['sources'].items():assert sha(repo/name)==h
    assert sha(repo/'tools/nes_packet_queue.py')==m['driver_sha256']
    inputs={}
    for name,e in m['inputs'].items():
        b=(repo/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(repo/e['path'])==e['sha256']
        assert b==bytes(int(s,16) for s in (run/(name+'.hex')).read_text().split())
        inputs[name]=b
    rows=[list(map(int,line.split())) for line in (run/'ownership.tsv').read_text().splitlines()]
    assert all(len(r)==14 for r in rows) and all(a[0]<b[0] for a,b in zip(rows,rows[1:]))
    observed=bytearray();writes=0;commits=0;concurrent=0;errors=Counter();states=0
    for row in rows:
        cycle,reset,pop,pa,pe,cop,ca,ce,valid,data,state,ready,active,epoch=row
        if reset:
            assert not(pa or ca or pe or ce or valid or state or ready or active)
        else:
            if pe:assert not pa;errors['p'+str(pe)]+=1
            if ce:assert not(ca or valid);errors['c'+str(ce)]+=1
            if valid:
                assert cop==2 and ca and active and not ce
                observed.append(data)
            else:assert data==0
            if pop==2 and pa:writes+=1
            if cop==3 and ca:commits+=1;assert not active
            if pop==2 and pa and valid:concurrent+=1
            for i in range(2):
                before=(states>>(i*2))&3;after=(state>>(i*2))&3
                assert before==after or (before,after) in ((0,1),(1,2),(2,3),(3,0)),(cycle,before,after)
        states=state
    def pattern(f,n):return bytes((i*17+f*29)&255 for i in range(n))
    expected=inputs['split']+inputs['sprite']+inputs['resident']+pattern(4,1)+pattern(5,3072)
    expected+=inputs['resident'][:3]+b''.join(pattern(n,n%31+1) for n in range(3,66))
    assert bytes(observed)==expected
    assert writes==m['metrics']['writes']==10492
    assert len(observed)==m['metrics']['reads']==10460 and commits==68 and concurrent>0
    assert set(errors)=={'p1','p2','p3','p4','p5','p6','c3','c4','c5','c7','c8'}
    return dict(candidate=m['candidate'],actual_rtl_pass=True,checks=m['metrics']['checks'],
       writes=writes,read_bytes=len(observed),commits=commits,concurrent_write_read_edges=concurrent,
       aborted_reset_unread_bytes=writes-len(observed),payload_sha256=hashlib.sha256(expected).hexdigest(),
       error_observations=dict(errors),source_hashes=m['sources'],input_packets=m['inputs'],
       raw_result_sha256=sha(run/'result.json'),verifier_sha256=sha(__file__),
       clock_domain='one synchronous10ns test clock',board_timing_proven=False,
       cdc_implemented=False,snes_frontend_connected=False,core014_changed=False,
       scope='Actual original RTL transport/ownership;byte integrity and reset guards. No NES execution or SNES DMA/co-simulation/fit proof.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('run','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();r=verify(a.run,Path(__file__).resolve().parents[1])
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_hashes','input_packets')},indent=2))
