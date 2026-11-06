"""Split the MMC643-equivalent schedule at equal map/OBJ work; retain physical measurements separately."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_output615 import ROOT, csv_groups, group, ms, one, packets, read, run, sha
from analyze_nes_hardware552 import inputs
from nes_schedule492 import funcs


def spare_bus(lo, hi, transactions, queue, durations):
    """Idle SPI spans at <=2 outstanding heads; keep all measured transactions in place."""
    edges = Counter()
    for start, end in transactions:
        if lo < end and start < hi:
            edges[max(lo,start)] += 1
            edges[min(end,hi)] -= 1
    # Three or four existing ordinary heads leave too little reserved credit.
    for start,end in queue:
        if lo < end and start < hi:
            edges[max(lo,start)] += 1
            edges[min(end,hi)] -= 1
    spans = []
    busy = 0
    last = lo
    edges[hi] += 0
    for t,change in sorted(edges.items()):
        if busy == 0 and t > last:
            if spans and spans[-1][1] == last:
                spans[-1] = (spans[-1][0],t)
            else:
                spans.append((last,t))
        busy += change
        last = t
    assert busy==0
    i=0
    for start,end in spans:
        while i < len(durations) and start+durations[i] <= end:
            start += durations[i]
            i += 1
    largest = max((b-a for a,b in spans), default=0)
    return dict(span_ms=ms(hi-lo),idle_ms=sum(ms(b-a) for a,b in spans),
                largest_ms=ms(largest),
                reorder_wire_ceiling_ms=ms(sum(d for d in durations if d<=largest)),
                optimistic_in_order_prefix=i, prefix_wire_ms=ms(sum(durations[:i])))


def tail(folder):
    commands = packets(folder)
    cpu = csv_groups(folder / "window.csv")
    events = read(folder / "events.json")
    transactions = [(e["start"], e["clock"]) for e in events if e["event"]=="SPI"]
    fifo = Counter()
    for g,cmds in commands.items():
        acks=[r for r in cpu[g] if r["event"]=="ack"]
        for (h,_,push),ack in zip(cmds,acks,strict=True):
            assert (h[0], h[1])==(ack["op"],ack["section"]) and push<=ack["clock"]
            fifo[push]+=1
            fifo[ack["clock"]]-=1
    blocked=[]
    used=0
    for clock, change in sorted(fifo.items()):
        if used<=2 and used+change>=3:
            closed=clock
        elif used>=3 and used+change<=2:
            blocked.append((closed,clock))
        used+=change
        assert 0<=used<=4
    assert used==0
    result = {}
    for g in (952, 954, 955, 957):
        rows = cpu[g]
        seal = [r for r in rows if r["op"] == 3]
        load, upload, wait, wake, ack = [
            one(seal, event) for event in ("load", "upload165_entry", "wait169", "wait_return_2999", "ack")]
        assert wake["line"] == 225 and load["clock"] < upload["clock"] <= wait["clock"] < wake["clock"] < ack["clock"]
        cmds = commands[g]
        last_work = max(i for i, (h, _, _) in enumerate(cmds) if h[1] == 2 or h[0] == 7)
        tail_cmds = cmds[last_work+1:-1]
        assert tail_cmds and cmds[-1][0][0] == 3
        start, end = cmds[last_work][2], cmds[-1][2]
        e1 = [e for e in events if e["event"] == "SPI" and e["generation"] == g and e["opcode"] == "0xe1"]
        wire = Counter()
        durations=[]
        for h, _, t in tail_cmds:
            e, = [e for e in e1 if abs(e["clock"] - t) <= 1]
            assert e["bytes"] == len(h)+3
            wire[f"{h[0]}/{h[1]}"] += ms(e["clock"]-e["start"])
            durations.append(e["clock"]-e["start"])
        owner=[e for e in events if e["generation"]==g]
        enter=one(owner,"output_enter531")["clock"]
        planner=one(owner,"planner_enter")["clock"]
        end_enter=one(owner,"end_enter")["clock"]
        assert planner < end_enter < enter < start
        last_packet_ack = max(r["clock"] for r in rows if r["event"]=="ack" and r["op"]!=3)
        # First wait targets scanline 225. Use the short/long NTSC period as a
        # bounded alignment comparison; this does not move the intervening DMA.
        phase_lead = [ms(t - (wake["clock"] - wait["clock"])) for t in (262*1364-4, 262*1364)]
        result[g] = dict(load_line=load["line"], upload_line=upload["line"], wait_line=wait["line"],
                         tail_op_section_counts=dict(Counter(f"{h[0]}/{h[1]}" for h,_,_ in tail_cmds)),
                         tail_E1_ms_by_op_section=wire, tail_E1_ms=sum(wire.values()),
                         last_map_or_bulk_push_to_SEAL_push_ms=ms(end-start),
                         last_ordinary_ACK_to_SEAL_load_ms=ms(load["clock"]-last_packet_ack),
                         previous_line225_alignment_ms=phase_lead,
                         planner_to_output=spare_bus(planner,enter,transactions,blocked,durations),
                         after_plan_to_last_map_or_bulk=spare_bus(end_enter,start,transactions,blocked,durations),
                         end_service_to_output=spare_bus(end_enter,enter,transactions,blocked,durations),
                         output_to_last_map_or_bulk=spare_bus(enter,start,transactions,blocked,durations))
    return result


def analyze(a):
    physical = read(ROOT/"analysis/hardware644-mmc643.json")
    game, budget, _, hashes = inputs(a.physical, 643)
    assert hashes == physical["source_SHA256"] and game["run_passed"] == "1"
    calls, _, high, low, _ = map(int, budget["cost_phase_02"].split(","))
    clocks = (high << 32) + low
    measured_ms = 1000 * clocks / int(budget["cost_clock_hz"]) / calls
    assert calls == int(game["native_frames"]) and abs(measured_ms-physical["phases"]["output_final_ack"]["ms_per_display"])<1e-9
    package = read(ROOT/"analysis/reject643-package.json")
    assert physical["source_SHA256"] and physical["terminal"]["retires_EA"] == physical["display"]["completed"]
    assert sha(a.arm643/"sd2snes.elf") == package["ELF"] and sha(a.arm643/"firmware.stm") == package["firmware_SHA256"]
    linked = funcs(a.arm643/"sd2snes.elf")
    assert len(linked) == 798 and linked == funcs(a.arm638/"sd2snes.elf")
    reference = read(ROOT/"analysis/output615-verification.json")
    cases = {}
    for case in read(ROOT/"analysis/front638-verification.json")["cases"]:
        selected = case["modes"]["both"]
        folder = a.traces / selected["run"]
        schedule = selected["schedule"]
        assert selected["pass_all"] and schedule["image"] == sha(a.arm638/"firmware.stm")
        assert schedule["client"] == sha(folder/"client.sfc") == package["ROM_read"]["client"]
        joint = read(folder/"joint.json")
        assert joint["passed"] and joint["commits"] == joint["map_WRAM_VRAM_verified"] == 53
        assert joint["firmware_SHA256"] == schedule["image"] and joint["last_status"] == 1 and joint["max_bulk_banks"] <= 2
        frames = run(folder, schedule["pins"])
        assert {str(g):r["work"] for g,r in frames.items()} == reference["matched_work_SHA256"]
        # Check that the elapsed 'checks' and 'wait' buckets contain no counted DMA.
        for g, rows in csv_groups(folder/"window.csv").items():
            if g not in frames:
                continue
            seal = [r for r in rows if r["op"]==3]
            upload = one(seal,"upload165_entry")["clock"]
            waiting = False
            for r in seal:
                if r["event"] == "wait169":
                    waiting = True
                elif r["event"].startswith("wait_return_") or r["event"] == "final_upload212_same_blank212":
                    waiting = False
                elif r["event"] in ("ppu_dma","ppu_last"):
                    assert not waiting and r["clock"] >= upload
        cases[folder.name] = dict(boot=case["boot"],phase=case["phase"],start=schedule["parameters"]["start"],
            pins={**schedule["pins"],**{f:sha(folder/f) for f in ("packets.jsonl","obj-phases.json")}},
            warm=group([frames[g] for g in range(907,958)]), dense=group([frames[g] for g in range(951,956)]),
            watched={g:frames[g] for g in (951,952,953,954,955,957)}, tail=tail(folder),
            dense_intervals=schedule["intervals"], last_ACK=schedule["last_ACK"])
    assert len(cases)==4
    return dict(physical_phase=physical["phases"]["output_final_ack"],physical_internal_breakdown=None,
                matched_work_SHA256=reference["matched_work_SHA256"],functions_matched=len(linked),
                reference_613={k:v for k,v in reference["groups"].items() if k.startswith("613_")},cases=cases,
                scope="Four archived accepted-capture schedules with identical ARM functions, client and map/OBJ work. Physical sample has no per-frame CPU/DMA timestamps. No rejected-capture or hardware execution in this analysis.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("traces","arm638","arm643","physical","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
