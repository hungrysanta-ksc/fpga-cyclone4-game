"""Run the final ARM link on the exact 905/906 E8 samples and byte-checked E9 grants."""
import argparse
import json
from pathlib import Path
from analyze_nes_credit965 import measured
from check_nes_blank959 import directory, read, sha
from nes_arm964 import ARM
from nes_feedback953 import evidence
from nes_page963 import simulate
from nes_writable965 import wire
from nes_writable965 import prepare as make_fixtures
from test_nes_banks557 import MASTER, batches, crc, host_after


def capture(folder):
    record={}
    for g in (905,906):
        proof=measured(folder,g)
        packets=wire(folder,g)
        assert proof['differences']==0 and len(proof['grants'])==len(packets)
        samples=evidence(folder,g,log_name='mail964.log',all_polls=True)
        assert len(samples)==proof['polls']
        events=[e for e in read(folder/'events.json') if e.get('generation')==g and e.get('opcode')=='0xe9']
        record[g]=dict(log=proof['log_sha'],
                       polls=[[at,flags,n,desc.hex() if any(desc) else ''] for (_,at),(flags,n,desc) in sorted(samples.items())],
                       grants=[[round(e['start']),r['at'],packet] for e,r,(_,packet) in zip(events,proof['grants'],packets,strict=True)])
    return record


def run(temp,phase,cache,record,*,tail=None,work=ARM,edition=955,tag=None):
    polls={(int(g),at):(flag,n,bytes.fromhex(data) if data else bytes(12))
           for g,v in record.items() for at,flag,n,data in v['polls']}
    grants={int(g):v['grants'] for g,v in record.items()}
    used=set()
    sealed=set()
    changed=[]
    def wrap(parent):
        class Wire(parent):
            def snapshot557(self,tx,start):
                g=self.generation
                if g not in grants or tx[0] not in (0xe8,0xe9):
                    out=super().snapshot557(tx,start)
                    key=g,round(host_after(start+7.5*MASTER/2625000,3))
                    if tx[0]==0xe8 and tail and not changed and key in tail:
                        flags,n,desc=tail[key]
                        assert n==int.from_bytes(out[4:6],'big')
                        new=bytearray(out)
                        new[3],new[6:18]=flags,desc
                        new[19]=crc(new[1:19],8,7,0)
                        if new!=out:
                            changed.append(key)
                        return bytes(new)
                    return out
                sample=host_after(start+7.5*MASTER/2625000,3)
                self.rpc(sample)
                out=bytearray(self.response(tx))
                if tx[0]==0xe9:
                    expected,_,packet=grants[g][self.accepted]
                    assert round(start)==expected and tx.hex()==packet
                    self.e9_snapshot557=sample
                else:
                    key=g,round(sample)
                    flags,n,desc=polls[key]
                    assert key not in used and self.accepted==n
                    used.add(key)
                    out[3:18]=bytes([flags])+n.to_bytes(2,'big')+desc
                    out[19]=crc(out[1:19],8,7,0)
                return bytes(out)
            def seal557(self,tx,t):
                g=self.generation
                if g not in grants:
                    return super().seal557(tx,t)
                n=self.accepted
                _,edge,packet=grants[g][n]
                assert tx.hex()==packet and abs(edge-t)<2 and (g,n) not in sealed
                sealed.add((g,n))
                queue=batches(self)
                assert len(queue)==n
                queue.append(dict(seal=t,sample=self.e9_snapshot557,count=tx[3],first=self.plan_at))
        return Wire
    tag=tag or ('965measured' if tail is None else '965tail')
    simulate(temp,phase,cache,True,work,True,feedback=wrap,tag=tag,edition=edition)
    assert used==polls.keys() and len(sealed)==sum(map(len,grants.values()))
    if tail is not None:
        folder=directory(temp,phase,tag,cache)
        (folder/'tail965.json').write_text(json.dumps(changed))


def tail_fixtures(temp,phase,source):
    make_fixtures(temp,'965tail',(phase,),include_initial=True)
    original=directory(temp,phase,source,'cold')
    actual=directory(temp,phase,'965tail','cold')
    [(first,edge)]=read(actual/'tail965.json')
    assert first==910
    for g in range(905,first):
        a,b=original/f'gen{g}',actual/f'gen{g}'
        for name in ('wire914.hex','batch914.txt','polls914.txt','tokens914.txt','cap914.txt',
                     'sizes914.txt','expected914.hex','chr914.hex','origin914.txt','mail964.txt'):
            assert sha(a/name)==sha(b/name),(g,name)
        if g<=906:
            assert sha(a/'admission954.txt')==sha(b/'admission954.txt')
        # Grants beyond this lease cannot alter the saved rows. Include the
        # complete simulated lease (even its idle cycles) up to the next origin.
        origin=int((a/'origin914.txt').read_text())
        next_origin=int((original/f'gen{g+1}'/'origin914.txt').read_text())
        last_poll=max(int(l.split()[0]) for l in (a/'polls914.txt').read_text().splitlines())
        last_return=max(int(l.split()[-1]) for l in (a/'tokens914.txt').read_text().splitlines())
        assert max(last_poll,last_return)+275<next_origin-origin
        grants=lambda path:[v for v in map(int,(path/'grants914.txt').read_text().splitlines()) if v<=next_origin-origin]
        assert grants(a)==grants(b)
    donor=original/'gen909/rows-out951.hex'
    (actual/'checkpoint965.txt').write_text(sha(donor)+'\n'+str(donor.resolve())+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',type=int,choices=(1,2))
    parser.add_argument('cache',choices=('cold','warm'))
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source',help='final RTL-verified schedule')
    group.add_argument('--record',type=Path,help='archived two-phase wire record')
    parser.add_argument('--tail',action='store_true',help='also test the first later divergent E8 from the cold RTL replay')
    parser.add_argument('--tail-fixtures',action='store_true')
    a=parser.parse_args()
    if a.tail_fixtures:
        assert a.source and a.cache=='cold'
        tail_fixtures(a.temp,a.phase,a.source)
        raise SystemExit(0)
    if a.source:
        record=capture(directory(a.temp,a.phase,a.source,'cold'))
    else:
        record=read(a.record)[str(a.phase)]
    tail=None
    if a.tail:
        assert a.source and a.cache=='cold'
        tail={}
        for g in range(907,913):
            tail.update(evidence(directory(a.temp,a.phase,a.source,'cold'),g,log_name='mail964.log'))
    run(a.temp,a.phase,a.cache,record,tail=tail)
    if a.source and not a.tail:
        original=directory(a.temp,a.phase,a.source,a.cache)
        actual=directory(a.temp,a.phase,'965measured',a.cache)
        for name in ('events.json','window.csv','packets.jsonl','producer.jsonl','joint.json'):
            assert sha(actual/name)==sha(original/name),name
