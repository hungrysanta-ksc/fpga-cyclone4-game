"""Join direct-start, completion-polled, and baseline traces for the same 23-row capture."""
import argparse
import json
from pathlib import Path

from check_nes_dma1019 import records
from check_nes_output970 import packet_path
from check_nes_tail1013 import collect, guards
from nes_dma1019 import ROOT, WORK
from test_nes_raw506_joint import MASTER


def read(path):
    return json.loads(path.read_bytes())


def compare(temp):
    cases={}
    for phase in (1,2):
        name=f"nes-tile821-late-jointmirror-p{phase}-"
        ref=temp/(name+"1018wire-control")
        trial=temp/(name+"1019-e0")
        base,model=collect(ref)
        frames,joint=collect(trial)
        for g,frame in frames.items():
            for field in ("rgb","map","packet_digest","work"):
                assert frame[field]==base[g][field],(phase,g,field)
        assert joint["client_SHA256"]==model["client_SHA256"] and joint["ROM_read_allocations"]==model["ROM_read_allocations"]
        g=908
        events=[x for x in records(trial/"window.csv") if x["g"]==str(g)]
        shape=len(frames[g]["order"]),sum(p[0]==7 for p in frames[g]["order"])
        _,packet=packet_path(trial,g,expected_shape=shape)
        pair=[p for h,p in zip(frames[g]["order"],packet,strict=True) if h in ([2,5,1121,201],[2,5,1322,240])]
        map_heads=[p for h,p in zip(frames[g]["order"],packet,strict=True) if h[:2]==[2,2]]
        def stamp(r):
            return [int(r[k]) for k in ("clock","frame","line")]
        dmas=[stamp(x)+[int(x["value"])] for x in events if x["event"]=="ppu_dma" and int(x["clock"])<frames[g]["seal"][0]]
        checks=read(trial/"events.json")
        shape_flags=[[round(x["clock"]),bytes.fromhex(x["reply"])[2]] for x in checks
                     if x.get("opcode")=="0xe0" and map_heads[4]["arrive"]<=x["start"]<pair[0]["issue"]]
        start,=[r for r in dmas if r[-1]==192]
        selection=[x for x in events if x["event"]=="idle524" and int(x["value"])==65536+768]
        assert len(selection)==1 and int(selection[0]["clock"])<start[0]
        finish=next(stamp(x) for x in events if x["event"]=="ppu_last" and int(x["clock"])>start[0])
        progress=next(int(x["clock"]) for x in records(trial/"progress680.csv")
                      if int(x["clock"])>finish[0] and int(x["retired"])==map_heads[4]["index"])
        ack=next(clk for clk,flags in shape_flags if flags&8)
        assert start[0]<finish[0]<progress<=ack<pair[0]["issue"]
        raw=WORK.parent/f"p{phase}-normal"/"timing1019.json"
        ideal=read(WORK.parent/f"p{phase}-free"/"timing1019.json")
        duration=sum(w[2]-w[1] for w in ideal["section5_wire"])
        assert duration>22*1364
        cases[phase]=dict(shared=read(raw),free=ideal,arm=dict(map_heads=map_heads,pair=pair,
            flags_between_map_and_section5=shape_flags,preseal_DMA=dmas,map_end=finish,
            progress=progress,first_matching_E0=ack,seal=frames[g]["seal"],
            last_DMA=stamp([x for x in events if x["event"]=="ppu_last"][-1]),
            show=frames[g]["show"],ack=frames[g]["ack"],end_ack=frames[912]["ack"],
            advance_ms={k:round((base[g][k][0]-frames[g][k][0])*1000/MASTER,4) for k in ("seal","show","ack")},
            end_ack_advance_ms=round((base[912]["ack"][0]-frames[912]["ack"][0])*1000/MASTER,4),
            checked_captures=len(frames),work=frames[g]["work"],allocated_reads=joint["ROM_read_allocations"]),
            pair_wire_clocks=duration,max_clocks_lines225_through246=22*1364)
    return dict(baseline="MMC1012",master_Hz=MASTER,phases=cases,guards=guards("e0",root=WORK),
                direct_trigger_faults={fault:read(WORK.parent/f"p{p}-{fault}"/"timing1019.json")
                    for p,fault in [(1,"stop_decode"),(2,"bad_seal")]})


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    args=p.parse_args()
    (ROOT/"analysis/dma1019-results.json").write_text(json.dumps(compare(args.temp),indent=2)+"\n",newline="\n")
