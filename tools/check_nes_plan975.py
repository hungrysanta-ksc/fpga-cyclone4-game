"""Correlate generation 911 input, plan, ROM grants and display on both boot phases."""
import argparse
import json
from pathlib import Path

from analyze_nes_palette971 import measure
from check_nes_blank959 import directory, read, sha
from check_nes_output970 import counters, packet_path, replay
from nes_plan975 import BASE, KEYS, WORK
from test_nes_banks557 import MASTER

MODES = {"973before232": BASE, "975defer": WORK, "975keys": KEYS}
FAULTS = {"bad_seal": 224, "stop_decode": 228}


def milliseconds(clocks):
    return round(clocks*1000/MASTER, 6)


def inspect(folder, ref):
    metrics = measure(folder, ref)
    events = read(folder/"events.json")
    def unique(name):
        event, = (e for e in events if e["generation"]==911 and e["event"]==name)
        return event
    commit = max(e["clock"] for e in events if e.get("input_generation")==911 and e.get("opcode")=="0xd2")
    planner = unique("planner_enter")["clock"]
    e9, = (e for e in events if e["generation"]==911 and e.get("opcode")=="0xe9")
    records, = (r["records"] for r in read(folder/"e9931.json") if r["g"]==911)
    assert len(records)==15 and records[0][:2]=="82" and records[-1][:2]=="83"
    _, ledger = packet_path(folder, 911)
    tile = metrics["tiles911"]
    assert [(r["kind"],r["bytes"]) for r in tile]==[(0,16),(1,32),(1,384)]
    owned = dict(read(folder/"returns904.json"))
    spi = sum(max(0,min(e["clock"],e9["start"])-max(e["start"],planner))
              for e in events if "start" in e)
    grant = [r for r in read(folder/"grants904.json") if r[0]==911]
    reveal = metrics["reveal_vblank"]
    seal = counters(folder,911)
    return dict(clocks=dict(last_D2=commit, planner=planner, E9_issue=e9["start"], E9_accept=e9["clock"],
                            first_BG_ready=tile[0]["producer"], first_OBJ_ready=tile[1]["producer"],
                            last_OBJ_ready=tile[2]["producer"], OBJ_returns=[owned[r["token"]] for r in tile[1:]],
                            SEAL=seal["load"],display=seal["reveal"],ACK912=metrics["ack912"]),
                ms=dict(D2_to_planner=milliseconds(planner-commit),planner_to_E9=milliseconds(e9["start"]-planner),
                        SPI_before_E9=milliseconds(spi),outside_SPI_before_E9=milliseconds(e9["start"]-planner-spi),
                        E9_wire=milliseconds(e9["clock"]-e9["start"]),
                        E9_accept_to_first_OBJ=milliseconds(tile[1]["producer"]-e9["clock"]),
                        planner_to_SEAL=milliseconds(seal["load"][0]-planner)),
                demand_grants=grant,records=records,tile=tile,packet_order=[(r["op"],r["section"]) for r in ledger],
                displays=reveal,interval911=reveal[6]-reveal[5],six_intervals=reveal[-1]-reveal[1],
                rgb_matches=metrics["rgb_matches"],firmware_sha256=metrics["arm_sha256"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--mode",choices=list(MODES)[1:])
    p.add_argument("--guard",choices=FAULTS)
    a=p.parse_args()
    if a.guard:
        if not a.mode:p.error("--guard requires --mode")
        folder=directory(a.temp,1,a.mode,"cold")
        packets,_=packet_path(folder,911)
        replay(a.temp,folder,a.out,"control",packets,911,a.guard)
        return
    result={"clock_Hz":MASTER,"phases":{},"flash_B":{},"guards":{}}
    for phase in (1,2):
        ref=directory(a.temp,phase,"973before232","cold")
        data=result["phases"][phase]={k:inspect(directory(a.temp,phase,k,"cold"),ref) for k in MODES}
        assert all(x["records"]==data["973before232"]["records"] for x in data.values())
        profile=directory(a.temp,phase,"975profile","cold")
        for name in ("events.json","window.csv","producer.jsonl","records.bin"):
            assert sha(profile/name)==sha(ref/name),name
        marks=read(a.temp/f"nes-plan975-p{phase}.json")
        assert any(k=="finish_obj810" for k,_ in marks)
        result.setdefault("baseline_function_entry",{})[phase]=marks
    for k,v in MODES.items():
        binary,=(v/"link").rglob("firmware.stm")
        result["flash_B"][k]=binary.stat().st_size
        assert result["flash_B"][k]<=212992
        if k=="973before232":continue
        guards=result["guards"][k]={}
        for fault,expected in FAULTS.items():
            value=read(a.temp/f"nes-{k}-{fault}"/"result.json")
            assert value["passed"] and value["commits"]==6 and value["last_status"]==expected
            guards[fault]=[value["commits"],expected]
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
