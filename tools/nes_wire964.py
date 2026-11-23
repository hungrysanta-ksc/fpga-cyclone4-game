"""Replay the received EB serial bytes and retain the real row RAM between leases."""
import argparse
import json
from pathlib import Path
from fixture_nes_port914 import fixture
from check_nes_blank959 import read, directory
from nes_arm964 import ARM
from nes_feedback953 import evidence
from nes_page963 import simulate
from test_nes_banks557 import MASTER, crc, host_after


def fixtures(temp,tag,phases=(1,2)):
    for p in phases:
        folder=directory(temp,p,tag,'cold')
        sends={g:(at,raw) for g,_,at,raw in read(folder/'hint963.json')['hints']}
        for g in range(905,913):
            d=folder if g==912 else folder/f'gen{g}'
            fixture(temp,p,True,g,tag,include_bg=True,earlier_origin=sends[g][0]-2048 if g in sends else None)
            origin=int((d/'origin914.txt').read_text())
            record=f'{sends[g][0]-origin} {sends[g][1]}' if g in sends else 'none'
            (d/'mail964.txt').write_text(record+'\n')


def feedback(temp,phase,source):
    # Reuse the prior prefix only while it has identical hardware-visible
    # responses. A changed reply invalidates all later samples in this trace.
    folder=directory(temp,phase,source,'cold')
    samples={}
    for g in (909,910,911,912):
        samples.update(evidence(folder,g,include_first_valid=g in (909,912),log_name='mail964.log'))
    used=[]
    def wrap(parent):
        class Measured(parent):
            def snapshot557(self,tx,start):
                before=super().snapshot557(tx,start)
                key=self.generation,round(host_after(start+7.5*MASTER/2625000,3))
                if tx[0]!=0xe8 or key not in samples or (used and used[-1]['changed']):
                    return before
                flags,accepted,descriptor=samples[key]
                assert accepted==int.from_bytes(before[4:6],'big')
                out=bytearray(before)
                out[3]=flags
                out[6:18]=descriptor
                out[19]=crc(out[1:19],8,7,0)
                used.append(dict(g=key[0],at=key[1],changed=out!=before,reply=out.hex()))
                return bytes(out)
        return Measured
    simulate(temp,phase,'cold',True,ARM,True,feedback=wrap,tag='964feedback')
    assert used
    (directory(temp,phase,'964feedback','cold')/'feedback964.json').write_text(json.dumps(used))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--tag',default='963bnes-mail964both')
    p.add_argument('--feedback',type=int,choices=(1,2))
    args=p.parse_args()
    if args.feedback:
        feedback(args.temp,args.feedback,args.tag)
    else:
        fixtures(args.temp,args.tag)
