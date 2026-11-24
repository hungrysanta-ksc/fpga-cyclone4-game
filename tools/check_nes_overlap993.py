"""Correlate wire occupancy, observed queue credit, tile returns and receiver service."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from check_nes_output970 import counters
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_raw991 import measure
from nes_overlap993 import BASE, MODES, ROOT


def charge(q,ledger,events):
    start,end=q["issue"],q["arrive"]
    overlap=sum(max(0,min(end,r["ack"])-max(start,r["load"])) for r in ledger if r["index"]<q["index"])
    sent=sum(e.get("opcode")=="0xe1" and e["clock"]<=start+0.5 for e in events)
    credit=next(e for e in reversed(events) if e.get("opcode")=="0xe0" and e["clock"]<=start+0.5)
    retired=int.from_bytes(bytes.fromhex(credit["reply"])[5:7],"big")
    assert 0<=sent-retired<4 and overlap<=end-start
    return dict(issue=start,arrive=end,load=q["load"],retire=q["ack"],wire_ms=ms(end-start),
                overlap_ms=ms(overlap),known_free_at_issue=4-(sent-retired))


def analyze(temp):
    out={"phases":{},"guards":{},"flash_B":{}}
    for p in (1,2):
        ref=directory(temp,p,"978returned","cold")
        result=out["phases"][p]={}
        for mode in ("ref",*MODES):
            d=ref if mode=="ref" else directory(temp,p,"993"+mode,"cold")
            with patch("check_nes_raw991.directory",return_value=d):
                x=measure(temp,p,"trial",ref)
            cmds,ledger=packet_path(d,911)
            events=read(d/"events.json")
            returns=dict(read(d/"returns904.json"))
            chosen=[(cmd,q) for cmd,q in zip(cmds[-len(ledger):],ledger,strict=True)
                    if cmd[1]==3 or (q["section"]==5 and int.from_bytes(bytes.fromhex(cmd[3])[10:12],"little")>=1121)]
            assert [len(bytes.fromhex(cmd[3]))-16 for cmd,q in chosen]==[201,240,168]
            tails=[charge(q,ledger,events) for _,q in chosen]
            real=result[mode]=dict(tail=tails,OBJ_returns=[returns[n] for n in (29,30)],seal=x["seal"],
                reveal908=x["reveal908"],early909_B=x["early909_B"],capture_margin910_ms=x["margin910_ms"],
                reveal911=x["reveal911"],interval911=x["interval"],six=x["six"],ACK912=x["ACK912"],
                DMAs=x["DMAs"],arm_sha=x["link"],rom_sha=x["rom"])
            b=result["ref"]
            real["delta_OBJ_return_ms"]=[ms(v-w) for v,w in zip(real["OBJ_returns"],b["OBJ_returns"])]
            real["seal_gain_ms"]=ms(b["seal"][0]-x["seal"][0])
            real["ACK912_gain_ms"]=ms(b["ACK912"]-x["ACK912"])
            assert real["early909_B"]==624 and real["capture_margin910_ms"]>0 and real["reveal908"][1:]==[38,245]
            if mode!="ref":continue
            deadline=x["latest_seal_if_only_validation_and_color_remain"]
            real["latest_SEAL"]=deadline
            remaining=ledger[8:-1]
            assert ledger[7]["op"]==7 and ledger[7]["section"]==1
            # Keep the measured service time of each remaining receiver head.
            # Remove all gaps / bus time; this is conditional on 978's service costs.
            start=ledger[7]["ack"]+x["seal"][0]-ledger[-1]["load"]
            real["service_only_late_ms"]=[ms(start+sum(q["ack"]-q["load"] for q in remaining
                                                    if not drop or q["section"]!=5)-deadline) for drop in (False,True)]
            ready=read(Path("analysis/hdma990-results.json"))["phases"][str(p)]["ref"]["writes"]["packed_raw_final"]
            free=[];end=ready
            for e in events:
                if e.get("event")!="SPI" or e["clock"]<=ready or e["start"]>=returns[30]:continue
                free.append(max(0,e["start"]-end));end=e["clock"]
            free.append(max(0,returns[30]-end))
            real["longest_free_SPI_before_OBJ_return_ms"]=ms(max(free))
            real["all_free_SPI_before_OBJ_return_ms"]=ms(sum(free))
        instant=temp/f"nes-overlap993-both-instant2-p{p}"
        b=result["ref"]
        returned=dict(tuple(map(int,line.split())) for line in (instant/"returns970.txt").read_text().splitlines())
        assert [returned[i] for i in (29,30)]==b["OBJ_returns"]
        assert sha(instant/"frame-911.rgb")==sha(ref/"frame-911.rgb")
        x=counters(instant,911)
        result["fixed_OBJ_instant"]=dict(OBJ_returns=b["OBJ_returns"],seal=x["seal"],reveal=x["reveal"],ACK911=x["ack"],
                                        seal_gain_ms=ms(b["seal"][0]-x["seal"][0]),late_ms=ms(x["seal"][0]-b["latest_SEAL"]))
        for fault in ("stop3","live","damage"):
            d=temp/f"nes-overlap993-both-{fault}-p{p}"
            r=read(d/"result.json")
            assert r["passed"] and r["commits"]==6 and r["last_status"]=={"stop3":0,"live":228,"damage":224}[fault]
            assert sha(d/"retained.rgb")==sha(ref/"frame-910.rgb")
            out["guards"][f"{fault}-p{p}"]=[r["commits"],r["last_status"]]
    for m in ("ref",*MODES):
        arm=BASE if m=="ref" else ROOT/m
        out["flash_B"][m]=next((arm/"link").rglob("firmware.stm")).stat().st_size
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf8")
