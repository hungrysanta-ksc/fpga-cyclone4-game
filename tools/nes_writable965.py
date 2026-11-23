"""Feed RTL bank availability between successive seals, then check on the resulting wire schedule."""
import argparse
import json
import re
from pathlib import Path
from analyze_nes_chr951 import logtext
from check_nes_blank959 import directory, read
from nes_arm964 import ARM
from nes_page963 import simulate
from nes_wire964 import fixtures
from fixture_nes_port914 import fixture
from test_nes_banks557 import MASTER, batches, crc, host_after


def wire(folder,g):
    return [json.loads(l) for l in (folder/f'e9wire914-{g}.jsonl').read_text().splitlines()]


def transitions(folder,g):
    d=folder/f'gen{g}'
    s=logtext(d/'mail964.log')
    assert 'PASS914 trace' in s
    origin=int((d/'origin914.txt').read_text())
    packets=wire(folder,g)
    avail={int(n):int(k)+origin for n,k in re.findall(r'WRITABLE958 packets=(\d+) edge=(-?\d+)',s)}
    assert set(range(len(packets)+1))==avail.keys()
    end,=re.findall(r'END965 packets=\d+ edge=(\d+)',s)
    return {n:avail[n]-packets[n-1][0] for n in range(1,len(packets)+1)},origin+int(end)-packets[-1][0]


def partial_measurements(temp,p,attempt):
    folder=directory(temp,p,'965wire'+str(attempt),'cold')
    result={}
    for g in (905,906):
        d=folder/f'gen{g}'
        log=d/'mail964.log'
        if not log.is_file():
            continue
        s=logtext(log)
        assert 'PASS914 trace' in s or 'OPEN965 batch=' in s
        origin=int((d/'origin914.txt').read_text())
        observed=re.findall(r'WRITABLE958 packets=(\d+) edge=(\d+)|OPEN965 batch=(\d+) edge=(\d+)',s)
        seals=wire(folder,g)
        for n,k,early,opened in observed:
            index=int(n or early)
            if index:
                tick=int(k or opened)+origin
                result[g,index]=(tick-seals[index-1][0],tick-seals[0][0])
        for n,k in re.findall(r'BOX965 released=(\d+) edge=(\d+)',s):
            # The preceding batch can relinquish the mailbox before the new
            # bank is sealed. Preserve that edge when ARM moves the seal earlier.
            index=int(n)+1
            if attempt>=2 and index<=len(seals):
                result[g,index]=(None,int(k)+origin-seals[0][0])
        terminal=re.search(r'END965 packets=\d+ edge=(\d+)',s)
        if terminal:
            result[g,'end']=int(terminal[1])+origin-seals[0][0]
    return result


def run(temp,p,cache,source,tag):
    donor=directory(temp,p,source,'cold')
    timings={g:transitions(donor,g) for g in (905,906)}
    original={g:wire(donor,g) for g in timings}
    previous={}
    for attempt in range(1,int(tag.removeprefix('965wire'))):
        previous.update(partial_measurements(temp,p,attempt))
    def wrap(parent):
        class Measured(parent):
            def snapshot557(self,tx,start):
                g=self.generation
                if g not in timings or tx[0] not in (0xe8,0xe9):
                    return super().snapshot557(tx,start)
                sample=host_after(start+7.5*MASTER/2625000,3)
                self.rpc(sample)
                rows=batches(self)
                n=len(rows)
                assert n==self.accepted
                writable,done=timings[g]
                flag=1
                if n:
                    # Intervals are relative to the preceding seal. This prediction
                    # is used only if every E8 and all moved E9 pass the NEW RTL trace.
                    shift=rows[0]['seal']-original[g][0][0]
                    anchor=rows[-1]['seal'] if writable[n]<2 else original[g][n-1][0]+shift
                    ready_at=anchor+writable[n]
                    end_at=original[g][-1][0]+shift+done
                    if (g,n) in previous:
                        age,relative=previous[g,n]
                        ready_at=(rows[-1]['seal']+age if age is not None and age<2 else
                                  max(rows[-1]['seal'],rows[0]['seal']+relative))
                    if (g,'end') in previous:
                        end_at=rows[0]['seal']+previous[g,'end']
                    ended=n==len(original[g]) and sample>=end_at
                    flag=2 if ended else int(sample>=ready_at)
                out=bytearray(self.response(tx))
                if tx[0]==0xe9:
                    assert flag==1 and bytes(tx).hex()==original[g][n][1]
                    self.e9_snapshot557=sample
                else:
                    out[3]=flag
                    out[19]=crc(out[1:19],8,7,0)
                return bytes(out)

            def seal557(self,tx,t):
                if self.generation not in timings:
                    return super().seal557(tx,t)
                rows=batches(self)
                assert len(rows)==self.accepted and tx.hex()==original[self.generation][len(rows)][1]
                rows.append(dict(seal=t,sample=self.e9_snapshot557,count=tx[3],first=self.plan_at))
        return Measured
    simulate(temp,p,cache,True,ARM,True,feedback=wrap,tag=tag)


def prepare(temp,tag,phases=(1,2),include_initial=False):
    fixtures(temp,tag,phases)
    for p in phases:
        folder=directory(temp,p,tag,'cold')
        events=read(folder/'events.json')
        for g in (905,906):
            d=folder/f'gen{g}'
            if include_initial:
                first=min(e['start'] for e in events if e.get('generation')==g and e.get('opcode') in ('0xe8','0xe9'))
                fixture(temp,p,True,g,tag,include_bg=True,earlier_origin=int(first)-2048,initial_polls=True)
            origin=int((d/'origin914.txt').read_text())
            plans=wire(folder,g)
            es=[e for e in events if e.get('generation')==g and e.get('opcode')=='0xe9']
            lines=[]
            for index,(e,(end,body)) in enumerate(zip(es,plans,strict=True)):
                if index==0 and not include_initial:
                    continue
                assert end==e['clock']
                edges=[7.5]+[(4+k)*8+7.5 for k in range(len(bytes.fromhex(body))-8)]
                cycles=[round(host_after(e['start']+bits*MASTER/2_625_000,3))-origin for bits in edges]
                lines.append(' '.join(map(str,[index,*cycles])))
            (d/'admission954.txt').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('source')
    parser.add_argument('tag')
    parser.add_argument('--phase',type=int,choices=(1,2))
    parser.add_argument('--fixtures-only',action='store_true')
    parser.add_argument('--include-initial',action='store_true')
    parser.add_argument('--cache',choices=('cold','warm'),default='cold')
    args=parser.parse_args()
    if args.phase and not args.fixtures_only:
        run(args.temp,args.phase,args.cache,args.source,args.tag)
    else:
        prepare(args.temp,args.tag,(args.phase,) if args.phase else (1,2),args.include_initial)
