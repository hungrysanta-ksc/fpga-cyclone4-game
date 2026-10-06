# Independent CDC request/response trace reconciliation. SPDX-License-Identifier: MIT.
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re,statistics
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(run,repo):
    m=json.loads((run/'result.json').read_text())
    assert m['passed'] and all(v==0 for v in m['phases'].values())
    for name,h in m['output_hashes'].items():assert sha(run/name)==h
    for name,h in m['sources'].items():assert sha(repo/name)==h
    assert sha(repo/'tools/nes_packet_cdc.py')==m['driver_sha256']
    inp={}
    for name,e in m['inputs'].items():
        data=(repo/e['path']).read_bytes();assert len(data)==e['bytes'] and sha(repo/e['path'])==e['sha256']
        assert data==bytes(int(x,16) for x in (run/(name+'.hex')).read_text().split());inp[name]=data
    expected=inp['split']+inp['sprite']+inp['resident']+bytes((i*17+7*29)&255 for i in range(17))
    cases={}
    for label,meta in m['runs'].items():
        log=(run/(label+'.log')).read_text()
        assert meta['passed'] and len(meta['cases'])==13 and not re.search(r'\*\* (?:Fatal|Error):',log)
        pending=None;owned=False;data=bytearray();latencies=[];counts=Counter();canceled=[];packets={}
        for line in (run/(label+'.tsv')).read_text().splitlines():
            kind,*fields=line.split();v=list(map(int,fields));counts[kind]+=1
            if kind=='R':
                t,op,ep,seq,address=v
                assert pending is None,'duplicate request while outstanding'
                pending=dict(time=t,op=op,epoch=ep,seq=seq,address=address,reply=None)
            elif kind=='Q':
                t,op,ep,seq,address,accept,error,valid,byte=v
                assert pending is not None and pending['reply'] is None
                assert (op,ep,seq,address)==tuple(pending[k] for k in ('op','epoch','seq','address'))
                assert t>=pending['time']
                assert not(error and (accept or valid))
                assert not valid or op==2 and accept
                pending['reply']=(accept,error,valid,byte)
            elif kind=='H':
                t,op,ep,seq,accept,error,valid,byte,length,active,latency=v
                assert pending is not None and pending['reply']==(accept,error,valid,byte)
                assert (op,ep,seq)==tuple(pending[k] for k in ('op','epoch','seq'))
                assert latency==t-pending['time'] and latency>0
                if op==1 and accept:
                    assert not owned;owned=True
                    assert length==({1:2328,2:2052,3:2008}[seq] if ep==1 else 4 if ep==2 else 17)
                if valid:
                    assert owned;data.append(byte);latencies.append(latency)
                    key=(ep,seq)
                    p=packets.setdefault(key,dict(first_request=pending['time'],last_response=t,bytes=0))
                    p.update(last_response=t,bytes=p['bytes']+1)
                if op==3 and accept:assert owned;owned=False;counts['commits']+=1
                assert active==int(owned)
                if error:counts['error'+str(error)]+=1
                pending=None
            elif kind=='X':
                if pending:canceled.append(pending)
                pending=None;owned=False
            else:raise AssertionError(kind)
        assert pending is None and not owned and bytes(data)==expected
        assert len(data)==meta['metrics']['readbytes']==6405
        assert counts['H']==meta['metrics']['responses']==6426 and counts['commits']==4
        assert len(canceled)==2 and sum(bool(c['reply'] and c['reply'][2]) for c in canceled)==1
        assert counts['R']==counts['H']+len(canceled)
        assert set(k for k in counts if k.startswith('error'))=={'error3','error4','error5','error7','error8'}
        cases[label]=dict(clock=meta,counts=dict(counts),canceled_requests=len(canceled),
            reset_discarded_response_bytes=1,received_bytes=len(data),payload_sha256=hashlib.sha256(data).hexdigest(),
            accepted_read_response_latency_ns=dict(min=min(latencies),median=statistics.median(latencies),max=max(latencies)),
            payload_read_spans=[dict(epoch=ep,seq=seq,**p,span_ns=p['last_response']-p['first_request']) for (ep,seq),p in packets.items()])
    return dict(candidate=m['candidate'],passed=True,actual_rtl_runs=len(cases),cases=cases,
        independent_checked_bytes=len(expected)*len(cases),source_hashes=m['sources'],input_packets=m['inputs'],
        raw_result_sha256=sha(run/'result.json'),verifier_sha256=sha(__file__),
        common_reset_only=True,physical_cdc_constraints_or_mtbf_proven=False,
        snes_mmio_dma_connected=False,real_nes_snes_clock_strategy_resolved=False,
        scope='Actual RTL logical CDC behavior under3synthetic clock/phase pairs. Bundled data protocol;not metastability/board timing,standalone endpoint reset or SNESDMA proof.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('run','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();r=verify(a.run,Path(__file__).resolve().parents[1])
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=r['passed'],actual_runs=r['actual_rtl_runs'],bytes=r['independent_checked_bytes'],
          latencies={k:v['accepted_read_response_latency_ns'] for k,v in r['cases'].items()}),indent=2))
