"""Compare producer, wire and 65816 clocks for the same 911 image."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_palette971 import measure
from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_plan975 import FAULTS, directory, milliseconds, packet_path, read, sha
from nes_tail979 import work
from test_nes_raw506_joint import PERIOD


def display(trace):
    events=rows(trace/"window.csv")
    def last(g,event):
        return max((int(x["clock"]),int(x["frame"]),int(x["line"])) for x in events
                   if x["g"]==str(g) and x["event"]==event)
    reveal=last(911,"reveal")
    return dict(reveal908=last(908,"reveal"),reveal910=last(910,"reveal"),reveal911=reveal,
                seal=last(911,"seal"),upload=last(911,"upload165_entry"),
                dma=[[int(x[k]) for k in ("clock","frame","line","value")] for x in events
                     if x["g"]=="911" and x["event"]=="ppu_dma"],
                early909_B=sum(int(x["value"]) for x in events if x["g"]=="909" and x["event"]=="ppu_dma"
                               and int(x["frame"])<last(909,"reveal")[1]))


def timeline(trace,ref):
    full=measure(trace,ref)
    assert map_payloads(trace)==map_payloads(ref)
    expected=lambda d:[(r["g"],r["records"]) for r in read(d/"e9931.json")]
    assert expected(trace)==expected(ref)
    commands,ledger=packet_path(trace,911)
    commands=[c for c in commands if c[0]==911]
    for c,item in zip(commands,ledger,strict=True):
        h=bytes.fromhex(c[3])
        item["offset"]=int.from_bytes(h[10:12],"little")
        item["payload"]=int.from_bytes(h[12:14],"little")
        item["arrive_to_load_ms"]=milliseconds(item["load"]-item["arrive"])
        item["restore_and_ack_ms"]=milliseconds(item["ack"]-item["load"])
    tiles=[(c,r) for c,r in zip(commands,ledger) if r["op"]==7 and r["section"]==1]
    c,item=tiles[-1]
    token=int.from_bytes(bytes.fromhex(c[3])[16:20],"little")
    returned=dict(read(trace/"returns904.json"))[token]
    assert item["load"]<returned<item["ack"]
    marks=display(trace)
    spi=read(trace/"events.json")
    time=Counter()
    for e in spi:
        if e.get("event")=="SPI":
            overlap=min(e["clock"],marks["seal"][0])-max(e["start"],returned)
            if overlap>0:time[e["opcode"]]+=overlap
    duration=marks["seal"][0]-returned
    planner,=(e["clock"] for e in spi if e.get("generation")==911 and e["event"]=="planner_enter")
    e9,=(e for e in spi if e.get("generation")==911 and e.get("opcode")=="0xe9")
    assert all(p["producer"]<=p["observed"] for p in full["tiles911"])
    time["outside_SPI"]=duration-sum(time.values())
    assert time["outside_SPI"]>=0
    ready,=(e["capture_ready"] for e in spi if e["event"]=="source_begin" and e["generation"]==911)
    ack909=max(int(r["clock"]) for r in rows(trace/"window.csv") if r["g"]=="909" and r["event"]=="ack")
    target=ready-240*341*4
    target+=round((ack909-target)/PERIOD)*PERIOD
    commit=max(e["clock"] for e in spi if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    assert [(r["op"],r["section"]) for r in ledger[:3]]==[(1,0),(2,5),(5,5)]
    return dict(**marks,capture_margin_ms=milliseconds(target-commit),outstanding=ledger,
        last_OBJ_token=token,last_OBJ_return=returned,return_to_SEAL_ms=milliseconds(duration),
        planner_to_E9_issue_ms=milliseconds(e9["start"]-planner),E9_end=round(e9["clock"]),
        tile_ready=full["tiles911"],
        return_to_SEAL_breakdown_ms={k:milliseconds(v) for k,v in time.items()},
        displays=full["reveal_vblank"],six=full["reveal_vblank"][-1]-full["reveal_vblank"][1],
        ACK912=full["ack912"],firmware=full["arm_sha256"],rgb_matches=full["rgb_matches"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--guard-mode",required=True)
    a=p.parse_args()
    out={"phases":{},"flash_B":{},"guards":{}}
    for phase in (1,2):
        ref=directory(a.temp,phase,"978returned","cold")
        baseline=timeline(ref,ref)
        d=out["phases"][phase]={"978returned":baseline,"consumer":{}}
        for mode in ("tables","tables_oam","clear","fitted","fitted96"):
            r=timeline(directory(a.temp,phase,"979"+mode,"cold"),ref)
            r["ACK_change_ms"]=milliseconds(r["ACK912"]-baseline["ACK912"])
            d[mode]=r
        for mode in ("idle","tail","frame","last1","all1","all2","all3"):
            folder=a.temp/f"nes-979-{mode}-p{phase}"
            run=read(folder/"result.json")
            assert run["passed"] and run["commits"]==7
            for g in range(905,912):assert sha(folder/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb")
            r=d["consumer"][mode]=display(folder)
            assert r["reveal910"]==baseline["reveal910"]
    for mode in ("tables","oam","split","tables_oam","prefix","prefix96","clear","fitted","fitted96"):
        f,=(work(mode)/"link").rglob("firmware.stm")
        out["flash_B"][mode]=f.stat().st_size
    for fault,status in FAULTS.items():
        folder=a.temp/f"nes-979-{a.guard_mode}-{fault}"
        data=read(folder/"result.json")
        assert data["passed"] and data["commits"]==6 and data["last_status"]==status
        assert sha(folder/"retained.rgb")==sha(directory(a.temp,1,"979"+a.guard_mode,"cold")/"frame-910.rgb")
        out["guards"][fault]=dict(mode=a.guard_mode,status=status)
    a.out.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
