"""Test the causal limit with advance knowledge of the two real $420B writes."""
import argparse
import json
from pathlib import Path

from check_nes_dma1019 import records
from check_nes_output970 import packet_path, replay
from check_nes_tail1013 import collect
from nes_tail1013 import once
from nes_split1020 import WORK
from report_nes_split1020 import frame908


def compare(temp,phase):
    trace=temp/f"nes-tile821-late-jointmirror-p{phase}-1020-stream"
    control=temp/f"nes-tile821-late-jointmirror-p{phase}-1018wire-control"
    dest=temp/"nes-split1020-stream-grants"/f"p{phase}"
    g=908
    frames,_=collect(trace)
    base=frame908(control,collect(control)[0])
    r=frame908(trace,frames,base["vblank225"])
    assert r["prefix_lead"]>0
    headers=frames[g]["order"]
    commands,ledger=packet_path(trace,g,expected_shape=(len(headers),sum(h[0]==7 for h in headers)))
    cut=r["prefix"]["index"]
    assert r["map_head"]["index"]==cut+1 and r["table"]["index"]==cut+2

    def mark(lua):
        lua=once(lua,"local inflight=false","local map_gate=0\nlocal inflight=false")
        lua=once(lua,"if not inflight then",f"""if not inflight then
    if (sequence=={cut+1} and map_gate<1) or (sequence=={cut+2} and map_gate<2) then break end""")
        return once(lua,'sample516("ppu_dma",dmaLength)','''sample516("ppu_dma",dmaLength)
  if pending526 and pending526.g==908 and regs[0x4301]==0x18 then
   if pending526.off==0 and dmaLength==768 then map_gate=1;rpc() end
   if pending526.off==768 and dmaLength==192 then map_gate=2;rpc() end
  end''')

    timing=replay(temp,trace,dest,"two_map_starts",commands,g,observe=mark,schedule_after=cut)
    ev=[v for v in records(dest/"window.csv") if v["g"]==str(g)]
    starts=[list(map(int,line.split())) for line in (dest/"starts.txt").read_text().splitlines()]
    actual=[]
    for offset,length in ((0,768),(768,192)):
        i,=[i for i,x in enumerate(ev) if x["event"]=="idle524" and int(x["value"])==65536+offset]
        trigger=next(x for x in ev[i+1:] if x["event"]=="ppu_dma")
        end=next(x for x in ev[i+1:] if x["event"]=="ppu_last")
        assert int(trigger["value"])==length and int(trigger["frame"])==38
        actual.append([int(trigger["clock"]),int(end["clock"]),int(trigger["line"]),int(end["line"])])
    assert starts[0][1]==actual[0][0] and starts[1][1]==actual[1][0]
    assert starts[0][2]-starts[0][1]==commands[cut][-1] and starts[1][2]-starts[1][1]==commands[cut+1][-1]
    return dict(clock225=base["vblank225"],clock247=base["line247"],prefix=r["prefix"],wire=starts[:2],
                map_DMA=actual,overlap=min(starts[1][2],actual[1][1])-starts[1][1],timing=timing,
                last_ppu_byte=next([int(x[k]) for k in ("clock","frame","line")] for x in reversed(ev) if x["event"]=="ppu_last"))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args()
    (WORK/f"stream-grant-{a.phase}.json").write_text(json.dumps(compare(a.temp,a.phase),indent=2))
