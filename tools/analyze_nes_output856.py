"""Compare real 5-second bins and two same-input replays without adding overlapping waits."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from analyze_nes_map830 import load, packets, window
from analyze_nes_output822 import CLK_MS
from analyze_nes_output852 import measure

ROOT = Path(__file__).resolve().parents[1]


def physical(path):
    raw = path.read_bytes()
    fields = dict(line.split("=", 1) for line in raw.decode().splitlines() if "=" in line)
    assert fields["cost_scene_crc32_hex"] == "a58fe808"
    assert fields["failed_transfers"] == fields["cost_crc_errors"] == "0"
    assert fields["tick_ms"] == "10" and fields["bin_ticks"] == "500"
    rows = []
    for k in range(6, 12):
        data = [int(x, 16) for x in fields[f"b{k:02d}"].split(",")]
        rows.append(dict(zip(fields["columns"].split(","), data, strict=True)))

    def per_frame(group):
        frames = sum(r["frames"] for r in group)
        result = {k: round(sum(r[k] for r in group) / frames, 5)
                  for k in ("bg", "obj", "mapdirty")}
        for k in ("recv", "plan", "seal"):
            result[k + "_ms"] = round(sum(r[k] for r in group) * 10 / frames, 5)
        return dict(frames=frames, **result)

    return dict(sha256=hashlib.sha256(raw).hexdigest(), display=fields["display_1_30_60"],
                half=per_frame(rows), bins={30+5*i: per_frame([r]) for i,r in enumerate(rows)})


def overlap(start, end, left, right):
    return max(0, min(end, right) - max(start, left))


def paired_duration(events, begin, finish):
    selected = [e for e in events if e["event"] in (begin, finish)]
    assert len(selected) % 2 == 0
    spans = []
    for a, b in zip(selected[::2], selected[1::2]):
        assert a["event"] == begin and b["event"] == finish and b["clock"] >= a["clock"]
        spans.append(b["clock"] - a["clock"])
    return spans


def credit_windows(spi, events):
    """Intervals with four issued heads and no ARM-visible free slot."""
    ack = {e["index"]: e["clock"] for e in events if e["event"]=="ack"}
    sent = retired = 0
    full = None
    windows = []
    for e in spi:
        if e["opcode"] == "0xe1":
            sent += 1
            assert sent-retired <= 4
            if sent-retired == 4:
                assert full is None
                full = (e["clock"], ack[retired+1])
        elif e["opcode"] == "0xe0":
            response = bytes.fromhex(e["reply"])
            assert int.from_bytes(response[3:5], "big") == sent
            observed = int.from_bytes(response[5:7], "big")
            assert retired <= observed <= sent
            if full is not None and observed > retired:
                start, first_ack = full
                end = e["clock"]
                assert first_ack <= end+1
                windows.append((start, max(start,min(first_ack,end)), end))
                full = None
            retired = observed
    assert full is None and sent == retired
    return windows


def replay(temp, edition, phase):
    tag = f"856-{edition}"
    d = temp / f"nes-tile821-demo-jointmirror-p{phase}-{tag}-on"
    metrics, geometry, _ = measure(temp, "demo", phase, "on", tag, column=True)
    package = load(ROOT / f"analysis/trial{edition}-package.json")
    assert metrics["arm"] == package.get("ARM", package.get("arm"))
    assert metrics["client"] == package["client"]
    spans = load(d / "output-spans.json")
    work = load(temp / "nes-comparison851/demo/demo/work.json")
    spi = [e for e in load(d / "events.json") if e["event"] == "SPI"]
    wire = [e for e in spi if e["opcode"] == "0xe1"]
    payloads = packets(d)
    assert len(wire) == len(payloads)
    group = defaultdict(list)
    for p in payloads:
        group[int.from_bytes(p[8:10], "little")].append(p)
    by_generation = defaultdict(list)
    events = window(d)
    full = credit_windows(spi, events)
    for e in events:
        by_generation[e["g"]].append(e)
    rows = {}
    assert len(work) == len(spans["phases"]) == 62
    prior_reveal = None
    for w, (start, end) in zip(work, spans["phases"]):
        g = w["g"]
        events = by_generation[g]
        show, = (e for e in events if e["event"] == "reveal")
        gap = show["frame"] - prior_reveal if prior_reveal is not None else None
        prior_reveal = show["frame"]
        if w["source_frame"] < 2560:
            continue
        head, = (e for e in events if e["op"] == 3 and e["event"] == "load")
        ack, = (e for e in events if e["op"] == 3 and e["event"] == "ack")
        issued = wire[head["index"] - 1]
        assert issued["packet_opcode"] == 3 and issued["generation"] == g
        cut, taken, done = issued["clock"], head["clock"], ack["clock"]
        assert start < cut <= taken < done <= end
        pre = [e for e in spi if e["clock"] > start and e["start"] < cut]
        by_op = Counter()
        for e in pre:
            by_op[e["opcode"]] += overlap(start, cut, e["start"], e["clock"])
        pauses = Counter()
        for left, right, reason, progress in spans["polls"]:
            width = overlap(start, cut, left, right)
            if width:
                # Guard SPI inside this function is already charged to the bus.
                for e in pre:
                    width -= overlap(max(start,left),min(cut,right),e["start"],e["clock"])
                assert width >= -0.01
                pauses[reason] += max(0, width)
        post = [e for e in events if taken <= e["clock"] <= done]
        dma = sum(paired_duration(post, "ppu_dma", "ppu_last"))
        waits = []
        for index, e in enumerate(post):
            if e["event"] == "wait169":
                resume = post[index+1]
                assert resume["event"] in ("wait_return_5781","wait_return_2999","final_upload212_same_blank212")
                waits.append(resume["clock"]-e["clock"])
        last_wait = waits[-1] if waits else 0
        pieces = dict(pre_SPI=sum(by_op.values()), pre_credit_pause=pauses[0],
                      pre_other_pause=sum(pauses.values())-pauses[0],
                      pre_other=cut-start-sum(by_op.values())-sum(pauses.values()),
                      SEAL_queue=taken-cut, SNES_service=done-taken-dma-sum(waits),
                      DMA=dma, prior_VBlank_wait=sum(waits)-last_wait,
                      last_VBlank_wait=last_wait, ARM_final=end-done)
        assert min(pieces.values()) >= -0.01 and abs(sum(pieces.values())-(end-start)) < 0.01
        def extent(p):
            if p[0] == 9:
                return 23 * 64
            pos = 12 if p[0] == 2 else 14
            return int.from_bytes(p[pos:pos+2], "little")
        ps = group[g]
        loads = {name: sum(extent(p) for p in ps if accept(p))
                 for name, accept in (("map_B", lambda p: p[1]==2 and p[0] in (2,4,9)),
                                      ("BG_B", lambda p: p[:2]==bytes((7,0))),
                                      ("OBJ_B", lambda p: p[:2]==bytes((7,1))))}
        assert loads["BG_B"] == 16*(1+w["bg_new"]) and loads["OBJ_B"] == 32*w["obj_new"]
        # Input SPI is often borrowed during output; it is a subset of this
        # wall time and must not be added to the DMA/VBlank decomposition.
        next_reads = [e for e in spi if e.get("input_generation", g) > g
                      and e["opcode"] in ("0xd0", "0xd1", "0xd2", "0xd3")]
        next_input_spi = sum(overlap(start, end, e["start"], e["clock"]) for e in next_reads)
        next_after_ack = sum(overlap(done, end, e["start"], e["clock"]) for e in next_reads)
        input_spi = sum(overlap(start, end, e["start"], e["clock"]) for e in spi
                        if e["opcode"] in ("0xd0", "0xd1", "0xd2", "0xd3"))
        tile_acks = [e for e in events if e["op"]==7 and e["section"]==1 and e["event"]=="ack"]
        column_spans = defaultdict(dict)
        for event in events:
            if event["section"]==2 and event["op"] in (2,4,9) and event["event"] in ("ack","load"):
                column_spans[event["index"]][event["event"]] = event["clock"]
        map_accept = sum(pair["ack"] - pair["load"] for pair in column_spans.values())
        rows[w["source_frame"]] = dict(
             full_queue_before_first_SNES_ACK_ms=round(sum(overlap(start,cut,a,b) for a,b,c in full)/CLK_MS,5),
             full_queue_until_ARM_observes_return_ms=round(sum(overlap(start,cut,b,c) for a,b,c in full)/CLK_MS,5),
             column_bundle=any(p[:2]==bytes((9,2)) for p in ps),
             map_service_ms=round(map_accept/CLK_MS,5),
             last_OBJ_ACK_to_SEAL_load_ms=round((taken-tile_acks[-1]["clock"])/CLK_MS,5) if tile_acks else None,
             final_DMA_B=sum(e["value"] for e in post if e["event"]=="ppu_dma"),**loads, gap=gap, ack=done, SEAL_line=head["line"],
             input_SPI_inside_output_ms=round(input_spi/CLK_MS,5),
             next_input_SPI_ms=round(next_input_spi/CLK_MS,5),
             next_input_SPI_after_ACK_ms=round(next_after_ack/CLK_MS,5),
             wait_lines=[e["line"] for e in post if e["event"]=="wait169"],
             ms={k: round(v/CLK_MS,5) for k,v in pieces.items()}, total_ms=round((end-start)/CLK_MS,5),
             pre_SPI_ms={k:round(v/CLK_MS,5) for k,v in by_op.items()})
    assert sum(r["gap"] for r in rows.values()) == metrics["display_VBlanks"]
    return rows, geometry


def analyze(temp, logs):
    hw = {v: physical(logs/f"nes-budget-mmc{v}.txt") for v in (826,855)}
    assert hw[826]["sha256"] == "e3697bafd3a022fa9897131503c42e807e37cdca3cd097756d30ee43edbecc8f"
    assert hw[855]["sha256"] == "7bbecf66e3ca8ce774c91530873e929f966e4150888b3fada7970be4ea54d89e"
    matches = {}
    for k, a in hw[826]["bins"].items():
        b = hw[855]["bins"][k]
        matches[k] = max(abs(b[n]/a[n]-1) for n in ("mapdirty","bg","obj"))
    phases = {}
    for phase in (1,2):
        a, ga = replay(temp,826,phase)
        b, gb = replay(temp,855,phase)
        assert a.keys()==b.keys() and len(a)==60
        def by_source(geometry):
            out = defaultdict(list)
            work = load(temp / "nes-comparison851/demo/demo/work.json")
            source = {w["g"]: w["source_frame"] for w in work}
            for g, row in geometry:
                out[source[g]].append(row)
            return out
        ranges_a, ranges_b = by_source(ga), by_source(gb)
        exact = [f for f in a if ranges_a[f]==ranges_b[f]
                 and all(a[f][k]==b[f][k] for k in ("map_B","BG_B","OBJ_B"))]
        assert len(exact) == 60
        def summary(rows):
            r=[rows[f] for f in exact]
            return dict(full_queue_overlay_ms={k:round(mean(v[k] for v in r),4) for k in
                            ("full_queue_before_first_SNES_ACK_ms","full_queue_until_ARM_observes_return_ms")},
                        next_input_SPI_ms=round(mean(v["next_input_SPI_ms"] for v in r),4),
                        next_input_SPI_after_ACK_ms=round(mean(v["next_input_SPI_after_ACK_ms"] for v in r),4),
                        input_SPI_inside_output_ms=round(mean(v["input_SPI_inside_output_ms"] for v in r),4),
                        matched_mean_ms={k:round(mean(v["ms"][k] for v in r),4) for k in r[0]["ms"]},
                        matched_total_ms=round(mean(v["total_ms"] for v in r),4),
                        VBlanks=sum(v["gap"] for v in rows.values()), final_ACK=rows[2619]["ack"],
                        matched_pre_SPI_ms={k:round(mean(v["pre_SPI_ms"].get(k,0) for v in r),4)
                                            for k in sorted(set().union(*(v["pre_SPI_ms"] for v in r)))})
        phases[phase]=dict(exact_source_frames=exact, same_map_ranges=ga==gb, MMC826=summary(a),
                           MMC855=summary(b), frames={"826":a,"855":b})
    return dict(scope="Real hardware provides frame-start 5-second bins. Replay uses the same source IDs, IRQ/SPI and ROM model, and MMC855 mean SPI calibration on both firmwares. Output is wall time from phase mark to phase return; pre-SEAL SPI, exclusive poll service, and remaining ARM time are disjoint. Queue occupancy, next-input SPI, and map acceptance are nested overlays. Final DMA is its first-to-last byte span; setup and publication are SNES service.", physical=hw, closest_physical_bin_start_s=min(matches,key=matches.get),
                max_relative_work_difference=matches, phases=phases)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("temp","logs","out"):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.logs),indent=2)+"\n")
