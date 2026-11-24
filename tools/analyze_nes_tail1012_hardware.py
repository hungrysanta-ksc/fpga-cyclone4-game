"""Join both physical MMC1012 packet traces to the same generation's display and STOP records."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from statistics import mean

from analyze_nes_display1010_hardware import fields
from read_nes_frame900 import BLANK, PERIOD
from read_nes_tail1012 import ARM_TICK, MS, decode

ROOT = Path(__file__).resolve().parents[1]


def analyze(directory, trial):
    paths = {k:directory/f"nes-{k}-mmc1012-{trial}차.{ext}" for k,ext in (
        ("frame","bin"),("budget","txt"),("game-last","txt"),("progress","txt"))}
    g = fields(paths["game-last"])
    b = fields(paths["budget"])
    times = dict((stage,int(t)) for stage,t in re.findall(
        r"MMC1012 seq=\d+ stage=(\w+) [^\r\n]*?elapsed_ms=(\d+)",paths["progress"].read_text()))
    stages = ["DISPLAY_NEXT","DISPLAY_STOPPED","STOP_DONE","BASE_DONE","MENU_PREPARED"]
    assert [times[k] for k in stages] == sorted(times[k] for k in stages)
    assert g["candidate"]=="NES-MMC1012" and g["native_result"]=="1"
    assert g["loaded_bytes"]==g["compared_bytes"]=="393216"
    assert all(g[k]=="1" for k in ("run_passed","verified","stop_ok","base_restored","safe_to_reload"))
    assert all(g[k]=="0" for k in ("run_error","run_stop_error","run_rom_error","trace_aborts"))
    assert b["failed_transfers"]=="0" and b["tick_ms"]=="10"
    counts=list(map(int,b["display_1_30_60"].split(",")))
    trace=decode(paths["frame"].read_bytes())
    rows=trace["rows"]
    assert not any(trace["dropped"]) and all(r["map"]==23 and "invalid" not in r for r in rows)
    samples=[]
    for s in trace["samples"]:
        r, = (r for r in rows if (r["tick"],r["generation"])==(s["tick"],s["generation"]))
        packets=s["packets"]
        a,t,o,z=packets[-4:]
        assert [(p["op"],p["section"],p["payload"]) for p in (a,t,o,z)]==[(2,5,201),(2,5,240),(9,4,116),(3,0,168)]
        assert z["ready"]<=o["first_credit_observed"]<=z["issue"]
        def elapsed(x,y):
            return round((x-y)*ARM_TICK,4)
        maps=[p for p in packets if p["section"]==2 and p["issue_after_last_tile_ms_bounds"][0]>0]
        samples.append(dict(generation=r["generation"],tick=r["tick"],slot=s["slot"],packet_count=len(packets),
            spacing_vb=round(r["spacing_ms"]/PERIOD),tile_to_seal_ms=r["last_tile_to_show_ms"]-r["seal_to_show_ms"],
            dma_to_show_ms=r["dma_to_show_ms"],late_map_B=sum(p["payload"] for p in maps),
            late_map_wire_call_ms=elapsed(sum(p["sent"]-p["issue"] for p in maps),0),
            table201_sent_to_credit_ms=elapsed(a["first_credit_observed"],a["sent"]),
            table240_sent_to_credit_ms=elapsed(t["first_credit_observed"],t["sent"]),
            OAM_sent_to_SEAL_ready_ms=elapsed(z["ready"],o["sent"]),
            OAM_sent_to_credit_ms=elapsed(o["first_credit_observed"],o["sent"]),
            OAM_credit_to_SEAL_issue_ms=elapsed(z["issue"],o["first_credit_observed"]),
            SEAL_ready_to_issue_ms=elapsed(z["issue"],z["ready"]),SEAL_transfer_ms=elapsed(z["sent"],z["issue"]),
            prev_blank_closed_before_seal_min_ms=max(0,PERIOD-BLANK-r["seal_to_show_ms"]-MS)))
    return dict(files={k:hashlib.sha256(path.read_bytes()).hexdigest() for k,path in paths.items()},
                display_stage_ms=times["DISPLAY_STOPPED"]-times["DISPLAY_NEXT"],counts=counts,
                fps=[counts[0]/29,counts[1]/30],displayed55=trace["displayed55"],valid_map23=len(rows),
                dropped=trace["dropped"],samples=samples,missing_slots=sorted({0,1}-{s["slot"] for s in samples}),
                at_stop={k:int(g[k]) for k in ("sink_window_sent","sink_window_retired","sink_window_error",
                                                "native_sink_error","plan_error","native_result")})


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    runs=[analyze(args.directory,t) for t in (1,2)]
    previous=json.loads((ROOT/"analysis/display1010-hardware.json").read_bytes())["runs"]
    report=dict(runs=runs,mean_delta_fps_vs_1010=[mean(r["fps"][i] for r in runs)-mean(r["fps"][i] for r in previous) for i in range(2)])
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
