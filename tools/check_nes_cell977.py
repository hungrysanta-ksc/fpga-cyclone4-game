"""Check full schedules, profile attribution and STOP at generation 911."""
import argparse
import json
from pathlib import Path

from analyze_nes_output970 import deadline
from check_nes_bg976 import map_payloads,same_trace
from check_nes_blank959 import rows
from check_nes_plan975 import FAULTS,directory,inspect,milliseconds,packet_path,read,replay,sha
from nes_cell977 import BASE,BUCKET,MID,WORD,WORK

MODES={"976hint":BASE,"977row":WORK,"977word":WORD,"977mid":MID}


def attribution(path):
    data=read(path)
    times=data["ticks"]
    groups={
        "cell_address_and_access":(16,141,143,146,153,154,155),
        "descriptor":(*range(172,191),"call:memset"),
        "reuse_row_search":(136,137,138,"call:memcmp"),
        "slot_function":("call:nes_resident211_slot",),
        "tag_function":("call:tile",),
        "map_word_function":("call:map_word185",),
    }
    assigned=[str(n) for group in groups.values() for n in group]
    assert len(assigned)==len(set(assigned))
    clocks={key:sum(times.get(str(n),0) for n in group) for key,group in groups.items()}
    clocks["other"]=sum(v for k,v in times.items() if k not in assigned)
    total=data["state"]["end"]-data["state"]["start"]
    assert abs(sum(clocks.values())-total)<1
    residual=total-sum(clocks[k] for k in ("slot_function","tag_function","map_word_function"))
    return dict(ms={k:milliseconds(v) for k,v in clocks.items()},total_ms=milliseconds(total),
                residual_ms=milliseconds(residual),source_line_ticks=times,executions=data["counts"])


def handoffs(d):
    events=read(d/"events.json")
    result={}
    for g in (910,911):
        returns=[e["clock"] for e in events if e.get("input_generation")==g and e.get("opcode")=="0xd2"]
        d2=returns[-1]
        following,=(e for e in events if e.get("event")=="source_begin" and e["generation"]==g+1)
        tail=[e for e in events if e["event"]=="SPI" and returns[-2]<e["clock"]<=d2]
        result[g]=dict(D2=d2,next_capture_ready=following["capture_ready"],next_input=following["clock"],
                       penultimate_to_final_ms=milliseconds(d2-returns[-2]),block_count=len(returns),
                       tail_opcodes=[e["opcode"] for e in tail])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--mode",choices=list(MODES)[1:])
    p.add_argument("--guard",choices=FAULTS)
    a=p.parse_args()
    if a.guard:
        if not a.mode:p.error("--guard requires --mode")
        d=directory(a.temp,1,a.mode,"cold")
        packets,_=packet_path(d,911)
        replay(a.temp,d,a.out,"control",packets,911,a.guard)
        return
    result={"phases":{},"guards":{},"flash_B":{}}
    for name,work in {**MODES,"977bucket":BUCKET}.items():
        f,=(work/"link").rglob("firmware.stm")
        result["flash_B"][name]=f.stat().st_size
        assert (f.stat().st_size<=212992)==(name in MODES)
    for phase in (1,2):
        ref=directory(a.temp,phase,"976hint","cold")
        same_trace(directory(a.temp,phase,"977profile","cold"),ref)
        sample=result["phases"][phase]={"baseline_profile":attribution(a.temp/f"nes-cell977-profile-p{phase}.json")}
        for name in MODES:
            d=directory(a.temp,phase,name,"cold")
            z=inspect(d,ref)
            assert map_payloads(d)==map_payloads(ref)
            plan=lambda folder:[(r["g"],r["records"]) for r in read(folder/"e9931.json")]
            assert plan(d)==plan(ref)
            # Compare placement of the scroll prefix/padding around the first tile.
            order=z["packet_order"]
            assert order[:4]==[(1,0),(2,5),(5,5),(7,0)]
            reveal,=(r for r in rows(d/"window.csv") if r["g"]=="908" and r["event"]=="reveal")
            sample[name]=dict(ms=z["ms"],clocks=z["clocks"],displays=z["displays"],
                six_intervals=z["six_intervals"],reveal908=[int(reveal[k]) for k in ("clock","frame","line")],
                interval911=z["interval911"],input=handoffs(d),rgb_matches=z["rgb_matches"],
                map_packets=len(map_payloads(d)),firmware_sha256=z["firmware_sha256"],
                remaining_ms=milliseconds(z["clocks"]["SEAL"][0]-deadline(d,911)["latest_load_same_cost"]))
    for name in list(MODES)[1:]:
        group=result["guards"][name]={}
        for fault,status in FAULTS.items():
            folder=a.temp/f"nes-{name}-{fault}"
            r=read(folder/"result.json")
            assert r["passed"] and r["commits"]==6 and r["last_status"]==status
            assert sha(folder/"frame-910.rgb")==sha(directory(a.temp,1,name,"cold")/"frame-910.rgb")
            group[fault]=status
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
