# SPDX-License-Identifier: MIT
"""Bound the benefit of deferring the leading map pair, preserving the real tile supplies."""
import argparse
from pathlib import Path
from types import SimpleNamespace
from analyze_nes_supply781 import measure
from replay_nes_tail779 import run


def replay(temp,phase,client,mesen):
    trace=temp/f"nes-grant783-lend-p{phase}"
    base=temp/f"nes-range778-763-p{phase}"
    r=measure(trace,base)
    end=r["ACK968"]+r["first_blank_end"]*21477272/1000
    def schedule(packets,tx,events):
        def offset(i):return int.from_bytes(packets[i][10:12],"little")
        maps=[i for i,h in enumerate(packets) if h[1]==2]
        assert [offset(i) for i in maps]==[256,448,1024,1216,2304,2496,3072,3264]
        a=maps[0];target=maps[2:6]
        # Keep original order of non-map traffic. All four target ranges
        # require the same validated final row data. Reclaim only the wire
        # occupied by the two postponed packets, with real four-credit service.
        assert maps[5]+1==maps[6] and maps[2:6]==list(range(maps[2],maps[5]+1))
        early=[i for i in range(a,maps[5]+1) if i not in maps[:2]]
        order=list(range(a))+early+maps[:2]+list(range(maps[5]+1,len(packets)))
        bounds={i:tx[i]["start"] for i in order if i not in target}
        bounds[maps[0]]=max(end,bounds[maps[0]])
        floor=next(e["clock"] for e in events if e["event"]=="end_enter")
        for i in target:bounds[i]=floor
        return a,order,tx[a]["start"],bounds
    run(SimpleNamespace(trace=trace,client=client,mesen=mesen,out=temp/f"nes-rows783-idle-p{phase}",
                        floor=True,hold=False,pack=False),schedule)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","client","mesen"):p.add_argument(k,type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args();replay(a.temp,a.phase,a.client,a.mesen)
