# SPDX-License-Identifier: MIT
"""Compare complete 787 boots against 786M capture edges and the two timing references."""
import argparse
import json
from pathlib import Path

from analyze_nes_capture785 import PERIOD, RANGES, csv_groups, frame, ms, one, read, sha


MODES = (
    "raw", "raster", "tile", "both", "bytes", "joint", "batch", "tail", "batch_tile",
    "packed", "packed_tile", "finish", "resume", "resume_tile", "rows", "rows_raster",
    "sealed_poll", "rearm", "compact_rows", "compact_raster",
)
FLASH_LIMIT = 212992


def schedule(folder, reference):
    result = frame(folder, reference)
    rows = csv_groups(folder / "window.csv")
    events = read(folder / "events.json")
    result["timing"] = {}
    packets = [bytes.fromhex(json.loads(line)[2]) for line in
               (folder / "packets.jsonl").read_text().splitlines()]
    origin = read(folder / "joint.json")["parameters"]["ROM_phase"]
    for g in (952, 954, 960, 969):
        prev = one([r for r in rows[g-1] if r["op"] == 3], "reveal")
        ev = [e for e in events if e.get("generation") == g]
        src = one(ev, "source_begin")
        d2 = [e["clock"] for e in events if e.get("opcode")=="0xd2" and e.get("input_generation")==g-1][-1]
        ack = one([r for r in rows[g-2] if r["op"]==3], "ack")["clock"]
        own_edge = ((ack - origin) // PERIOD + 1) * PERIOD + origin
        actual_edge = (int((d2 - origin) // PERIOD) + 1) * PERIOD + origin
        assert src["capture_ready"] == actual_edge + 240 * 341 * 4
        timeline = dict(previous_commit_after_ACK_ms=ms(d2-ack), previous_commit_edge_margin_ms=ms(own_edge-d2))
        for name, tick in (("capture_ready", src["capture_ready"]), ("receive", src["clock"]),
                           ("planner", one(ev, "planner_enter")["clock"])):
            timeline[name] = ms(tick - prev["clock"])
        for name in ("load", "validate181", "coverage212", "upload165_entry", "wait169", "reveal", "ack"):
            marks = [r for r in rows[g] if r["op"] == 3 and r["event"] == name]
            assert marks and (name == "wait169" or len(marks) == 1), (folder, g, name)
            times = [dict(ms=ms(r["clock"] - prev["clock"]), line=r["line"],
                          blank=r["frame"] - prev["frame"]) for r in marks]
            timeline[name] = times if name == "wait169" else times[0]
        timeline["DMA"] = [[r["frame"] - prev["frame"], r["line"], r["value"]]
                           for r in rows[g] if r["event"] == "ppu_dma"]
        if g == 969:
            timeline["heads"] = []
            for row in rows[g]:
                if row["event"] != "load":
                    continue
                pkt = packets[row["index"]-1]
                off = int.from_bytes(pkt[10:12], "little")
                if pkt[0] != 7 and not (pkt[1] == 2 and off in (1216, 2304, 2496)):
                    continue
                ack = one([r for r in rows[g] if r["index"] == row["index"]], "ack")
                timeline["heads"].append(dict(op=pkt[0], section=pkt[1], offset=off,
                    accepted_ms=ms(row["clock"]-prev["clock"]), accepted_line=row["line"],
                    returned_ms=ms(ack["clock"]-prev["clock"]), returned_line=ack["line"]))
        result["timing"][g] = timeline
    return result


def report(temp, probe, runs):
    refs = read(Path(__file__).resolve().parents[1] / "analysis/capture785.json")["phases"]
    from check_nes_decode787 import profile953
    sender=temp/"nes-output768-sender/joint-sender.json"
    base_profile=profile953(probe.parent/"nes-arbitrate786/arm-map_gapfit/src",sender)
    builds = {}
    for mode in MODES:
        obj = probe / ("arm-"+mode) / "src/obj-nes-100"
        builds[mode] = dict(flash=(obj/"firmware.stm").stat().st_size,
                            ELF=sha(obj/"sd2snes.elf"), firmware=sha(obj/"firmware.stm"))
        builds[mode]["decode953"]=profile953(obj.parent,sender)
        assert builds[mode]["decode953"]["state"]==base_profile["state"]
        if mode in runs:
            assert builds[mode]["flash"] <= FLASH_LIMIT
            guard = probe / ("guard-"+mode)
            for key, file in (("guards","guards.json"), ("cache","cache.json"), ("credit","credit.json"),
                              ("decode","decode.json")):
                proof = read(guard / file)
                assert (proof["guards"] if key=="guards" else proof)["firmware"] == builds[mode]["firmware"]
                builds[mode][key] = proof
    phases = {}
    for phase in (1, 2):
        base = temp / f"nes-range778-763-p{phase}"
        control = schedule(temp / f"nes-arbitrate786-map_gapfit-p{phase}", base)
        table = phases[phase] = {"786M": control}
        for mode in runs:
            folder = temp / f"nes-handoff787-{mode}-p{phase}"
            s = table[mode] = schedule(folder, base)
            assert s["matched_frames"] == 66 and s["firmware"] == builds[mode]["firmware"]
            s["D2_earlier_absolute_ms"] = ms(control["D2_clock"]-s["D2_clock"])
            s["D2_earlier_from_ACK_ms"] = round(control["ACK_to_D2_ms"]-s["ACK_to_D2_ms"],6)
            s["delta_ms"] = {}
            for ref in ("763","783G"):
                r = refs[str(phase)][ref]
                s["delta_ms"][ref] = dict(dense=round(s["dense_ms"]-r["dense_ms"],6),
                                          final970=ms(s["final970"]-r["final970"]))
            intervals = s["intervals"]
            gates = dict(geometry_credit=builds[mode]["decode"]["budget"]["empty_geometry"]==4,
                         edge=phase == 1 or (s["lead_ms"]>0 and s["D2_clock"]<control["edge_after_ACK"]),
                         displays=s["dense"][1:3]==[2,3] and all(intervals[g]==2 for g in (909,960,969)),
                         first_DMA=s["first969"]==[n for _,_,n in RANGES] and
                                   bool(s["map_start_lines"]) and max(s["map_start_lines"])<=252,
                         time=all(x<0 for ref in s["delta_ms"].values() for x in ref.values()))
            s["missed"] = [k for k,v in gates.items() if not v]
            stop = temp / f"nes-handoff787-stop-{mode}-p{phase}" / "proof.json"
            if stop.exists():
                proof = read(stop)
                assert proof["after_return"] and proof["map_offset"]==2496 and proof["commits"]==64
                assert proof["blanks_after_STOP"]>=3 and proof["last_packet_status"]==0
                assert proof["retained"]==sha(folder/"frame-968.rgb") and proof["client"]==sha(folder/"client.sfc")
                s["STOP"] = proof
    passing = [n for n in runs if all(not p[n]["missed"] for p in phases.values())]
    return dict(scope="Cold 905–970, linked Cortex-M4 and 685 65816; shared SPI/IRQ/ROM timing model. DMA coverage is destination-specific. Not hardware FPS.",
                reference_decode953=base_profile, builds=builds, phases=phases, passing_both=passing)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","probe","output"):
        p.add_argument(k,type=Path)
    p.add_argument("runs",choices=MODES,nargs="+")
    a=p.parse_args()
    a.output.write_text(json.dumps(report(a.temp,a.probe,a.runs),indent=2)+"\n",newline="\n")
