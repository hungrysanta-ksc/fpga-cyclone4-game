"""Join E1 issuance to the Mesen packet trace and compare fixed-producer schedules."""
import argparse
import json
from pathlib import Path

from check_nes_blank959 import directory, read, rows, sha
from check_nes_output970 import counters, ordinary_first, packet_path
from test_nes_banks557 import MASTER


def breakdown(trace, target):
    _, ledger = packet_path(trace, target)
    tiles = [json.loads(line) for line in (trace / "producer.jsonl").read_text().splitlines()]
    ready = max(t["producer"] for t in tiles if t["generation"] == target)
    totals = dict(wait_packet=0, wait_load=0, service=0)
    previous = ledger[0]["issue"]
    for p in ledger:
        arrive, load, ack = p["arrive"], p["load"], p["ack"]
        both = max(previous, arrive)
        assert both <= load <= ack
        for key, start, stop in (("wait_packet", previous, both), ("wait_load", both, load),
                                 ("service", load, load if p["op"] == 3 else ack)):
            totals[key] += max(0, stop - max(ready, start))
        previous = ack
    assert sum(totals.values()) == ledger[-1]["load"] - ready
    return dict(last_obj_ready=ready, ready_to_seal_load=totals, packets=ledger)


def deadline(trace, g):
    dma = [v for v in rows(trace / "seal528.csv") if v["g"] == str(g) and v["event"] == "dma" and v["port"] == "34"]
    color, = dma
    c = counters(trace, g)
    clk = int(color["clock"])
    # Visible scanlines 0..224 are each 1364 master clocks in this NTSC replay.
    # Using 1364 for line 240 can underestimate the boundary by four clocks.
    end = clk - 1364 * int(color["line"]) - int(color["h"])
    validation = c["upload165_entry"][0] - c["load"][0]
    tail = c["reveal"][0] - clk
    assert 225 <= int(color["line"]) <= c["reveal"][2] and 0 < tail < 37 * 1364
    return dict(prior_blank_end_approx=end, seal_load_to_upload=validation,
                palette_dma_start_to_reveal=tail, latest_load_same_cost=end-validation-tail)


def bus_schedule(trace, folder, target, mode):
    packets, _ = packet_path(trace, target)
    if mode in ("ordinary", "prelude", "reserved"):
        packets = ordinary_first(packets, target, mode != "ordinary")
    real = [e for e in read(trace / "events.json") if "start" in e and e.get("opcode") != "0xe1"]
    overlap = {}
    first_palette = None
    for line in (folder / "starts.txt").read_text().splitlines():
        seq, start, end, outstanding = map(int, line.split())
        assert 0 <= outstanding < 4
        p = packets[seq-1]
        assert p[0] == target and end-start == p[-1] and start >= p[-2]
        if first_palette is None and bytes.fromhex(p[3])[1] == 3:
            first_palette = start
        for e in real:
            covered = max(0, min(end,e["clock"]) - max(start,e["start"]))
            if covered:
                op = e["opcode"]
                overlap[op] = overlap.get(op,0) + covered
    if mode == "reserved":
        assert not overlap
    return dict(overlap_other_SPI_clocks={k:round(v) for k,v in overlap.items()},
                first_early_palette_start=first_palette)


def summarize(temp, prefix907, prefix911):
    phases = {}
    for phase in (1, 2):
        trace = directory(temp, phase, "966release", "cold")
        phase_result = {}
        phase_result["reference_sha256"] = {name: sha(trace / name) for name in
            ("client.sfc", "packets.jsonl", "events.json", "window.csv", "seal528.csv", "producer.jsonl")}
        for g, prefix, modes in ((907,prefix907,("control","tail","frame","ordinary")),
                                 (911,prefix911,("control","ordinary","prelude","reserved"))):
            base = breakdown(trace, g)
            base.update(deadline(trace, g))
            base["modes"] = {}
            for mode in modes:
                folder = Path(f"{prefix}-p{phase}-{mode}")
                trace_events = counters(folder, g)
                assert sha(folder / "client.sfc") == phase_result["reference_sha256"]["client.sfc"]
                assert read(folder / "result.json")["commits"] == g-904
                for h in range(905, g+1):
                    assert sha(folder / f"frame-{h}.rgb") == sha(trace / f"frame-{h}.rgb")
                if mode == "control":
                    assert trace_events == counters(trace, g)
                # Compare VBlank at the same generation boundary in every run.
                prev = counters(folder,g-1)["reveal"]
                assert prev == counters(trace,g-1)["reveal"]
                window = [r for r in rows(folder / "window.csv") if r["g"] == str(g)]
                base["modes"][mode] = dict(events=trace_events, display_interval=trace_events["reveal"][1]-prev[1],
                    preseal_dma=[int(r["value"]) for r in window if r["op"] != "3" and r["event"] == "ppu_dma"])
                base["modes"][mode].update(bus_schedule(trace,folder,g,mode))
                if mode == "reserved":
                    actual = dict(read(trace / "returns904.json"))
                    new = dict(tuple(map(int,s.split())) for s in (folder / "returns970.txt").read_text().splitlines())
                    base["modes"][mode]["tile_return_delta_clocks"] = {token:new[token]-actual[token] for token in (28,29,30)}
            phase_result[g] = base
        phases[phase] = phase_result
    return dict(master_hz=MASTER, clock_unit="SNES master clock", phases=phases)


def guards(temp, prefix):
    result = {}
    reference = directory(temp,1,"966release","cold")
    for fault, status in (("stop_decode",228),("bad_seal",224)):
        folder = Path(f"{prefix}-{fault}")
        actual = read(folder / "result.json")
        assert actual["passed"] and actual["commits"] == 6 and actual["last_status"] == status
        assert sha(folder / "retained.rgb") == sha(reference / "frame-910.rgb")
        result[fault] = dict(commits=6,status=status,retained_generation=910)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("temp", "prefix907", "prefix911", "fault_prefix", "payload_prefix", "result"):
        p.add_argument(name,type=Path)
    args = p.parse_args()
    result = summarize(args.temp,args.prefix907,args.prefix911)
    result["faults911"] = guards(args.temp,args.fault_prefix)
    for phase, values in result["phases"].items():
        values[911]["arm_payload"] = read(Path(f"{args.payload_prefix}{phase}.json"))
    args.result.write_bytes((json.dumps(result,indent=2)+"\n").encode())
