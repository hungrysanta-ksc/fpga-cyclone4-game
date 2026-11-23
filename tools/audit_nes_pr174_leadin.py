"""Compare every 905/906 E8 token with the actual descriptor at the same sample."""
import hashlib
import json
import re
import sys
from pathlib import Path

from analyze_nes_chr951 import ROOT, directory, logtext, port_log, sha
from test_nes_banks557 import MASTER, host_after


def audit(temp, phase, generation):
    folder = directory(temp, phase, '952checkedrows', 'cold')
    trace = folder / f'gen{generation}'
    log = trace / 'port952-checked.log'
    saved = json.loads((ROOT/'analysis/companion952-results.json').read_bytes())
    expected = saved['variants']['checkedrows']['cases'][f'cold{phase}']['rtl'][str(generation)]
    result = port_log(log)
    assert result['log'] == expected['log'] and not result['error'] and result['chunks_bytes_hits_grants']
    text = logtext(log)
    rows = [list(map(int,line.split())) for line in (trace/'polls914.txt').read_text().splitlines()]
    observed = {int(edge):int(token) for edge,token in re.findall(r'DESC914 edge=(\d+) local_token=(\d+)',text)}
    publishes = {int(k):(int(n),int(at)) for k,n,at in re.findall(r'PUB914 token=(\d+) bytes=(\d+) at=(\d+)',text)}
    origin = int((trace/'origin914.txt').read_text())
    events = [e for e in json.loads((folder/'events.json').read_bytes())
              if e.get('generation') == generation and e.get('event') == 'SPI']
    samples = {round(host_after(e['start'] + 7.5*MASTER/2625000,3)-origin):i
               for i,e in enumerate(events) if e['opcode']=='0xe8'}
    edges = {edge for edge,*_ in rows}
    assert observed.keys() <= edges <= samples.keys() and len(edges) == len(rows) == result['polls'][0]
    mismatches = []
    for edge, flags, accepted, model in rows:
        actual = observed.get(edge,0)
        if actual == model:
            continue
        token = actual or model
        count, publish = publishes[token]
        i = samples[edge]
        mismatches.append(dict(edge=edge,model_token=model,rtl_token=actual,bytes=count,
                               rtl_publication=publish,model_flags=flags,accepted_model=accepted,
                               next_recorded_SPI=[e['opcode'] for e in events[i+1:i+4]]))
    full = log.parent
    replay = temp/'nes-review174'/f'p{phase}'/f'gen{generation}'
    detail = logtext(replay/'all-e8.log')
    checked = port_log(replay/'all-e8.log')
    assert checked['polls']==result['polls'] and checked['published']==result['published']
    assert checked['chunks_bytes_hits_grants']==result['chunks_bytes_hits_grants'] and not checked['error']
    assert sha(replay/'wire914.hex')==sha(full/'wire914.hex')
    fields = re.findall(r'E8914 difference edge=(\d+) token=(\d+)/(\d+) flags=(\d+)/(\d+) count=(\d+)/(\d+)',detail)
    assert len(fields)==result['polls'][1]
    types={}
    first={}
    for values in fields:
        edge,rt,mt,rf,mf,rc,mc=map(int,values)
        assert rt==observed.get(edge,0) and samples[edge]+1<len(events)
        cause='+'.join(label for label,changed in [('token',rt!=mt),('flags',rf!=mf),('count',rc!=mc)] if changed)
        assert cause
        key=f'{cause} {rf}/{mf} -> '+events[samples[edge]+1]['opcode']
        types[key]=types.get(key,0)+1
        first.setdefault(key,edge)
    return dict(g=generation,phase=phase,samples=len(rows),different=result['polls'][1],
                same_token_other_fields=result['polls'][1]-len(mismatches),
                token_differences=mismatches,chunks_and_bytes=result['chunks_bytes_hits_grants'][:2],
                field_changes_and_next_model_SPI=types,first_edge_per_class=first,full_rtl_log_sha256=checked['log'],
                rtl_log_sha256=result['log'],polls_sha256=sha(trace/'polls914.txt'))


def probe_first_ready(temp,phase):
    """Change only the first observed writable flag; record the ARM's following SPI command."""
    from nes_companion952 import complete_row_set, replay, supply
    from test_nes_banks557 import crc
    ref=audit(temp,phase,905)
    edge=ref['first_edge_per_class']['flags 1/0 -> 0xe8']
    original=directory(temp,phase,'952checkedrows','cold')
    sample=int((original/'gen905/origin914.txt').read_text())+edge
    tag='pr174bounded'
    original_events=json.loads((original/'events.json').read_bytes())
    bus=[e for e in original_events if e.get('event')=='SPI']
    at=next(i for i,e in enumerate(bus) if e['opcode']=='0xe8' and round(host_after(e['start']+7.5*MASTER/2625000,3))==sample)
    first_e9=next(e for e in bus[at+1:] if e['opcode']=='0xe9')
    result={}
    class IssuedPlan(Exception):
        pass
    def tapped(parent):
        class FirstReady(supply(parent,'checked')):
            def snapshot557(self,tx,start):
                if result and tx[0]==0xe9:
                    sent=[e for e in self.cpu.events if e.get('event')=='SPI' and e.get('start',0)>sample]
                    result.update(next=sent[0]['opcode'] if sent else '0xe9',
                                  next_start=round(sent[0]['start'] if sent else start),
                                  next_E9_start=round(start),next_E9_generation=self.generation,
                                  payload_sha256=hashlib.sha256(tx).hexdigest())
                    raise IssuedPlan
                answer=super().snapshot557(tx,start)
                if tx[0]!=0xe8 or self.generation!=905 or round(host_after(start+7.5*MASTER/2625000,3))!=sample:
                    return answer
                assert answer[3]==0 and not answer[6]
                reply=bytearray(answer)
                reply[3]=1
                reply[19]=crc(reply[1:19],8,7,0)
                result['response']=reply.hex()
                return bytes(reply)
        return FirstReady
    try:
        with complete_row_set():
            replay(temp,phase,'cold','banked',wrap=tapped,tag=tag)
    except IssuedPlan:
        pass
    before=dict(response=bus[at]['reply'],next=bus[at+1]['opcode'],next_start=round(bus[at+1]['start']),
                next_E9_start=round(first_e9['start']),next_E9_generation=first_e9['generation'])
    assert result['next_E9_generation']==before['next_E9_generation']==905
    out=temp/'nes-review174'/f'p{phase}'/'first-ready.json'
    out.write_text(json.dumps(dict(sample=sample,before=before,after=result),indent=2)+'\n')


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[2]=='--first-ready':
        probe_first_ready(Path(sys.argv[1]),int(sys.argv[3]))
        sys.exit(0)
    cases=[audit(Path(sys.argv[1]),p,g) for p in (1,2) for g in (905,906)]
    evidence=dict(source='952 checkedrows; cold; full descriptor samples before 953 feedback',cases=cases,
                  samples=sum(c['samples'] for c in cases),different=sum(c['different'] for c in cases),
                  different_token=sum(len(c['token_differences']) for c in cases))
    evidence['first_ready']=[json.loads(p.read_bytes()) for p in sorted((Path(sys.argv[1])/'nes-review174').glob('p*/first-ready.json'))]
    assert len(evidence['first_ready'])==2
    for phase,r in enumerate(evidence['first_ready'],1):
        folder=directory(Path(sys.argv[1]),phase,'952checkedrows','cold')
        event,=[e for e in json.loads((folder/'events.json').read_bytes()) if e.get('opcode')=='0xe9'
                and round(e['start'])==r['before']['next_E9_start']]
        tx,=[bytes.fromhex(tx) for t,tx in map(json.loads,(folder/'e9wire914-905.jsonl').read_text().splitlines())
             if round(t)==round(event['clock'])]
        assert hashlib.sha256(tx).hexdigest()==r['after']['payload_sha256']
        r.update(phase=phase,E9_wire_bytes=len(tx),advance_ms=round((round(event['start'])-r['after']['next_E9_start'])*1000/MASTER,6))
    (ROOT/'analysis/pr174-leadin.json').write_text(json.dumps(evidence,indent=2)+'\n',newline='\n')
