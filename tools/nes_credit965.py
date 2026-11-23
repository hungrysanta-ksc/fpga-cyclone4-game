"""Return the first measured writable E8 to the unmodified MMC964 ARM in each lease."""
import argparse
import json
import re
from pathlib import Path
from analyze_nes_chr951 import logtext
from check_nes_blank959 import directory, read
from nes_arm964 import ARM
from nes_page963 import simulate
from nes_wire964 import fixtures
from test_nes_banks557 import MASTER, batches, crc, host_after

BASE='963bnes-mail964both'
FIRST='965first'
BOTH='965both'


def stimulus(temp,phase,g):
    source=directory(temp,phase,BASE if g==905 else FIRST,'cold')
    d=source/f'gen{g}'
    log=logtext(d/'mail964.log')
    assert 'PASS914 trace' in log
    diff=re.search(r'E8914 difference edge=(\d+) token=0/0 flags=1/0 count=(\d+)/(\d+)',log)
    assert diff and diff[2]==diff[3]
    at=int((d/'origin914.txt').read_text())+int(diff[1])
    index=int(diff[2])
    when,hexdata=json.loads((source/f'e9wire914-{g}.jsonl').read_text().splitlines()[index])
    return dict(at=at,index=index,tx=hexdata,baseline_end=when)


def run(temp,phase,last,cache):
    targets={g:stimulus(temp,phase,g) for g in range(905,last+1)}
    records={}
    def wrap(parent):
        class Observed(parent):
            pending965=None
            def snapshot557(self,tx,start):
                g=self.generation
                at=host_after(start+7.5*MASTER/2_625_000,3)
                spec=targets.get(g)
                if tx[0]==0xe9 and spec and g in records and 'end' not in records[g]:
                    assert self.accepted==spec['index'] and bytes(tx).hex()==spec['tx']
                    self.rpc(at)
                    self.e9_snapshot557=self.pending965=at
                    records[g].update(start=start,snapshot=at)
                    return self.response(tx)
                before=super().snapshot557(tx,start)
                if tx[0]!=0xe8 or not spec or round(at)!=spec['at']:
                    return before
                assert g not in records and before[3:6]==bytes([0,0,spec['index']]) and not any(before[6:18])
                after=bytearray(before)
                after[3]=1
                after[19]=crc(after[1:19],8,7,0)
                records[g]=dict(**spec,before=before.hex(),after=after.hex())
                return bytes(after)

            def seal557(self,tx,end):
                if self.pending965 is None:
                    return super().seal557(tx,end)
                g=self.generation
                rows=batches(self)
                assert len(rows)==self.accepted==targets[g]['index'] and bytes(tx).hex()==targets[g]['tx']
                rows.append(dict(seal=end,sample=self.pending965,count=tx[3],first=self.plan_at))
                records[g]['end']=end
                self.pending965=None
        return Observed
    tag=FIRST if last==905 else BOTH
    simulate(temp,phase,cache,True,ARM,True,feedback=wrap,tag=tag)
    assert all('end' in records[g] for g in targets)
    folder=directory(temp,phase,tag,cache)
    (folder/'credit965.json').write_text(json.dumps(records,indent=2)+'\n')


def prepare(temp,last):
    tag=FIRST if last==905 else BOTH
    fixtures(temp,tag)
    for phase in (1,2):
        folder=directory(temp,phase,tag,'cold')
        for key,r in read(folder/'credit965.json').items():
            d=folder/f'gen{key}'
            origin=int((d/'origin914.txt').read_text())
            end,packet=json.loads((folder/f'e9wire914-{key}.jsonl').read_text().splitlines()[r['index']])
            assert end==r['end'] and packet==r['tx']
            edges=[round(r['snapshot'])]+[round(host_after(r['start']+((4+k)*8+7.5)*MASTER/2625000,3))
                                          for k in range(len(bytes.fromhex(packet))-8)]
            (d/'admission954.txt').write_text(' '.join(str(x) for x in [r['index'],*(e-origin for e in edges)])+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('last',type=int,choices=(905,906))
    parser.add_argument('--phase',type=int,choices=(1,2))
    parser.add_argument('--cache',choices=('cold','warm'),default='cold')
    args=parser.parse_args()
    if args.phase:
        run(args.temp,args.phase,args.last,args.cache)
    else:
        prepare(args.temp,args.last)
