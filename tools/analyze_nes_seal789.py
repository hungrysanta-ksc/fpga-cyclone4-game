# SPDX-License-Identifier: MIT
"""Account for actual SEAL, read, transfer and final display in two continuous boots."""
import argparse
import json
from pathlib import Path

from analyze_nes_boundary788 import LIMIT, RANGES, capture_boundary, csv_groups, ms, one, read, result, sha
from prepare_nes_seal789 import MODES


def stage(folder):
    rows = csv_groups(folder / "window.csv")
    dma = csv_groups(folder / "seal528.csv")
    arm = read(folder / "events.json")
    phase = read(folder / "joint.json")["parameters"]["ROM_phase"]
    def mark(gen, tag):
        return one([x for x in rows[gen] if x["op"] == 3], tag)
    view = mark(930, "reveal")
    seal = mark(931, "load")
    final = mark(931, "wait_final516") if any(x["event"]=="wait_final516" for x in rows[931]) else mark(931, "final212")
    reveal = mark(931, "reveal")
    dma_frames = {x["clock"]: x["frame"] for x in rows[931] if x["event"]=="ppu_dma"}
    selected = [dict(blank=dma_frames[x["clock"]]-view["frame"],line=x["line"],h=x["h"],B=x["bytes"],
                     dest=x["dst"],port=x["port"],src=x["src"])
                for x in dma[931] if x["event"]=="dma" and seal["clock"]<=x["clock"]<=reveal["clock"]]
    t = mark(933, "reveal")["clock"]
    q = {x["event"]:x for x in arm if x.get("generation")==934}
    wire = [e for e in arm if e["event"]=="SPI" and e.get("input_generation")==934]
    timeline = {k:ms(v-t) for k,v in {
        "ready":q["source_begin"]["capture_ready"],
        "first_D1":next(e["start"] for e in wire if e["opcode"]=="0xd1"),
        "final_D2":[e for e in wire if e["opcode"]=="0xd2"][-1]["clock"],
        "planner":q["planner_enter"]["clock"], "BG_frozen":q["bg_map_frozen"]["clock"],
        "END":q["end_enter"]["clock"], "output":q["output_enter531"]["clock"],
        "SEAL":mark(934,"load")["clock"], "display":mark(934,"reveal")["clock"]}.items()}
    following = {}
    for g in (952,954,960):
        previous = mark(g-1, "reveal")["clock"]
        source = [x for x in arm if x.get("generation")==g]
        ready = one(source, "source_begin")["capture_ready"]
        planner = one(source, "planner_enter")["clock"]
        following[g] = dict(ready_ms=ms(ready-previous), planner_ms=ms(planner-previous),
                            seal_ms=ms(mark(g, "load")["clock"]-previous),
                            display_ms=ms(mark(g, "reveal")["clock"]-previous))
    return {"from_previous_display":following, "931":dict(interval=reveal["frame"]-view["frame"],SEAL_to_display_ms=ms(reveal["clock"]-seal["clock"]),
                       final_check_line=final["line"],final_check_to_display_blanks=reveal["frame"]-final["frame"],
                       post_SEAL_DMA=selected),
            "934":dict(interval=mark(934,"reveal")["frame"]-mark(933,"reveal")["frame"],from_933_display_ms=timeline),
            "input933":capture_boundary(arm,rows,933,phase)}


def analyze(temp, probe):
    root = Path(__file__).resolve().parents[1]
    ref = read(root/"analysis/capture785.json")["phases"]
    origin = read(root/"analysis/arbitrate786.json")["phases"]
    boards = probe.parent
    stock = boards/"nes-complete685/client01/sink165.sfc"
    builds = {}
    for name in MODES:
        obj = probe/f"link-{name}/src/obj-nes-100"
        b = builds[name] = dict(Flash_B=(obj/"firmware.stm").stat().st_size,ELF=sha(obj/"sd2snes.elf"),
                                firmware=sha(obj/"firmware.stm"))
        if b["Flash_B"] <= LIMIT:
            folder=probe/f"guard-{name}"
            for k in ("guards","cache","credit","decode"):
                evidence=read(folder/f"{k}.json")
                assert (evidence["guards"] if k=="guards" else evidence)["firmware"]==b["firmware"]
                b[k]=evidence
            if name.endswith("_cost"):
                b["range_cost_guard"]=read(probe/f"{name}-cost.json")
                assert b["range_cost_guard"]["firmware"]==b["firmware"]
            if name in ("control_cost","first_wait_cost","first_bulk_cost","bulk_cost"):
                guard=read(probe/f"{name}-owner.json")
                assert guard["firmware"]==b["firmware"]
                b["owner_guard"]=guard["cases"]
    images = {"685":sha(stock), "789":sha(probe/"client/sink165.sfc")}
    data = read(probe/"client/build.json")
    client={k:data[k] for k in ("masks","physical_free_B","body_bytes","extra_raw_call_stack_B","new_persistent_WRAM_B")}
    phases={}
    for i in (1,2):
        p=str(i)
        runs=phases[p]={}
        baseline=temp/f"nes-range778-763-p{p}"
        for name in ("787Q","788Q","first","control_cost","first_wait_cost","first_bulk_cost","bulk_cost","Q-raw","first_wait_cost-raw","control_cost-raw"):
            f = temp/(f"nes-handoff787-sealed_poll-p{p}" if name=="787Q" else
                      f"nes-boundary788-owner_split_fit-p{p}" if name=="788Q" else f"nes-seal789-{name}-p{p}")
            image=probe/"client/sink165.sfc" if name.endswith("-raw") else stock
            v=result(f,baseline,image)
            if name.removesuffix("-raw") in builds:
                assert v["firmware"]==builds[name.removesuffix("-raw")]["firmware"]
            elif name in ("788Q","Q-raw"):
                assert v["firmware"]==sha(boards/"nes-boundary788/arm-owner_split_fit/src/obj-nes-100/firmware.stm")
            w = runs[name] = {k:v[k] for k in ("firmware","verified","display_VBlanks","dense_ms","final970","map_lines","first","seal_stages")}
            w.update(stage(f))
            w["prior_input"]={g:{k:x[k] for k in ("edge_margin_ms","popped_before_ACK","final_D2_from_ACK_ms","commit_clock")} for g,x in v["input"].items()}
            w["client"]=sha(image)
            w["D2_953_advance_vs_786M_ms"]=ms(origin[p]["map_gapfit"]["D2_clock"]-v["input"][953]["commit_clock"])
            w["D2_953_local_margin_ms"]=v["input"][953]["edge_margin_ms"]
            w["delta_ms"]={n: dict(dense=round(w["dense_ms"]-ref[p][n]["dense_ms"],6),
                                   ACK970=ms(w["final970"]-ref[p][n]["final970"])) for n in ("763","783G")}
            disp=w["display_VBlanks"]
            checks={"display":all(disp[g]==2 for g in (909,953,960,969)) and disp[952]<=3 and disp[954]==3,
                    "first496":w["first"]==[n for _,_,n in RANGES] and w["map_lines"] and max(w["map_lines"])<=252,
                    "D2_953":i==1 or (v["input"][953]["commit_clock"]<origin[p]["map_gapfit"]["edge_after_ACK"]
                                        and w["D2_953_local_margin_ms"]>0),
                    "dense_ACK":all(t<0 for pair in w["delta_ms"].values() for t in pair.values())}
            w["missed"]=[k for k,v in checks.items() if not v]
            if name not in ("787Q","788Q"):
                stop=read(temp/f"nes-seal789-stop-{name}-p{p}/proof.json")
                assert stop["client"]==sha(image) and stop["retained"]==sha(f/"frame-968.rgb")
                assert stop["commits"]==64 and stop["after_return"] and stop["map_offset"]==2496
                assert stop["blanks_after_STOP"]>=3
                w["map_STOP"]=stop
        fixed=temp/f"nes-seal789-fixed-p{p}"
        proof=read(fixed/"proof789.json")
        assert proof["client"]==images["789"] and proof["frames"]==66
        frows=csv_groups(fixed/"window.csv")
        def display(g):return one([x for x in frows[g] if x["op"]==3],"reveal")
        runs["fixed_arrivals"] = dict(proof=proof,interval931=display(931)["frame"]-display(930)["frame"],
                                    display931=display(931)["clock"],ACK970=one([x for x in frows[970] if x["op"]==3],"ack")["clock"])
    stop=[read(temp/f"nes-seal789-fixed-p{p}-checked{row}/proof789.json") for p,row in ((1,0),(2,2))]
    assert all(x["frames"]==26 and x["client"]==images["789"] for x in stop)
    return dict(scope="two 905-970 ARM/65816 boots, shared SPI, IRQ and ROM model", builds=builds,
                images=images,client=client,STOP=stop,phases=phases,
                passing=[n for n in phases["1"] if n!="fixed_arrivals" and all(not ph[n]["missed"] for ph in phases.values())])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","probe","out"):p.add_argument(k,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+"\n",newline="\n")
