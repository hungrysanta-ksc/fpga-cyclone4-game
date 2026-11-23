"""Measure the checked handoff and distinguish DMA spill from final status polling."""
import argparse
import json
from pathlib import Path

from analyze_nes_output970 import deadline
from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_plan975 import FAULTS,directory,inspect,milliseconds,packet_path,read,replay,sha
from nes_capture978 import MID,work
from test_nes_raw506_joint import PERIOD


def dma_and_capture(folder, reference):
    z=inspect(folder,reference)
    assert map_payloads(folder)==map_payloads(reference)
    assert [(r["g"],r["records"]) for r in read(folder/"e9931.json")]==[
        (r["g"],r["records"]) for r in read(reference/"e9931.json")]
    assert z["packet_order"][:4]==[(1,0),(2,5),(5,5),(7,0)]
    events=read(folder/"events.json")
    beam=rows(folder/"window.csv")
    def last(g,event):
        return max((int(r["clock"]),int(r["frame"]),int(r["line"])) for r in beam if r["g"]==str(g) and r["event"]==event)
    ack=last(909,"ack")[0]
    reveal=last(909,"reveal")
    returns=[e for e in events if e.get("input_generation")==910 and e.get("opcode")=="0xd2"]
    assert len(returns)==18
    end=returns[-1]["clock"]
    tail=[e for e in events if e.get("event")=="SPI" and returns[-2]["clock"]<e["clock"]<=end]
    polls=[e for e in tail if e.get("opcode")=="0xe0"]
    valid=[e for e in polls if bytes.fromhex(e["reply"])[3:5]==bytes.fromhex(e["reply"])[5:7]]
    assert valid==polls[-1:]
    e0,=valid
    suffix=tail[tail.index(e0):]
    assert [e["opcode"] for e in suffix]==["0xe0","0xea","0xe8","0xd3","0xd0","0xd1","0xd2"]
    assert e0["start"]>=ack
    ready,=(e["capture_ready"] for e in events if e.get("event")=="source_begin" and e["generation"]==911)
    start=ready-240*341*4
    target=start+round((ack-start)/PERIOD)*PERIOD
    assert start-PERIOD<=end<start
    pre=[[int(r["clock"]),int(r["line"]),int(r["value"])] for r in beam if
         r["g"]=="909" and r["event"]=="ppu_dma" and int(r["frame"])<reveal[1]]
    return dict(firmware=z["firmware_sha256"],RGB=z["rgb_matches"],scroll_first=True,
        reveal908=last(908,"reveal"),reveal909=reveal,ACK909=ack,polls=len(polls),
        E0_offsets_from_ACK=[[round(e["start"]-ack),round(e["clock"]-ack)] for e in polls],
        handoff=[[e["opcode"],round(e["start"]),round(e["clock"])] for e in suffix],
        ACK_to_E0_start_ms=milliseconds(e0["start"]-ack),E0_start_to_D2_ms=milliseconds(end-e0["start"]),
        capture_margin_ms=milliseconds(target-end),instant_poll_margin_ms=milliseconds(target-end+e0["start"]-ack),
        target_capture=target,actual_capture=start,early_DMA909=pre,
        early_DMA909_B=sum(d[2] for d in pre),displays=z["displays"],six=z["six_intervals"],
        interval911=z["interval911"],ACK912=z["clocks"]["ACK912"],planner911=z["clocks"]["planner"],
        seal_load911=z["clocks"]["SEAL"],
        seal_events911={event:last(911,event) for event in ("seal","validate181","coverage212","upload165_entry","wait169","reveal","ack")},
        seal_late_ms=milliseconds(z["clocks"]["SEAL"][0]-deadline(folder,911)["latest_load_same_cost"]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--guard",choices=FAULTS)
    p.add_argument("--mode",default="returned")
    a=p.parse_args()
    if a.guard:
        d=directory(a.temp,1,"978"+a.mode,"cold")
        cmd,_=packet_path(d,911)
        replay(a.temp,d,a.out,"control",cmd,911,a.guard)
        return
    result={"phases":{},"flash_B":{},"guards":{}}
    for ph in (1,2):
        ref=directory(a.temp,ph,"976hint","cold")
        out=result["phases"][ph]={}
        for m in ("976hint","977mid","978paced","978early","978hold","978bank","978returned"):
            d=directory(a.temp,ph,m,"cold")
            row=out[m]=dma_and_capture(d,ref)
            row["ACK912_delta976_ms"]=milliseconds(row["ACK912"]-out["976hint"]["ACK912"])
    for m in ("early","hold","idle","grant","bank","returned"):
        binary,=(work(m)/"link").rglob("firmware.stm")
        result["flash_B"][m]=binary.stat().st_size
    for fault,status in FAULTS.items():
        d=a.temp/f"nes-978{a.mode}-{fault}"
        r=read(d/"result.json")
        assert r["passed"] and r["commits"]==6 and r["last_status"]==status
        assert sha(d/"frame-910.rgb")==sha(directory(a.temp,1,"978"+a.mode,"cold")/"frame-910.rgb")
        result["guards"][fault]=dict(mode=a.mode,status=status,retained_generation=910)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
