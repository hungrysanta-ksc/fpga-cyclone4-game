"""Attribute repeated queue-status replies and compare identical adjacent source frames."""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import json
from pathlib import Path

from analyze_nes_input848 import CLOCK_MS, stats
from analyze_nes_map830 import packets, window
from check_nes_game478 import sha
from test_nes_raw506_joint import PERIOD


def consumer_intervals(rows):
    """Only pair explicit VBlank waits and DMA transactions whose last byte was logged."""
    spans = []
    waiting = dma = None
    for row in rows:
        event, t = row["event"], row["clock"]
        if event == "wait169":
            assert waiting is None
            waiting = t
        elif waiting is not None:
            assert event.startswith("wait_return_") or event == "final_upload212_same_blank212"
            spans.append((waiting, t, "VBlank_wait"))
            waiting = None
        if event == "ppu_dma":
            dma = t
        elif event == "ppu_last":
            assert dma is not None and dma < t
            spans.append((dma, t, "observed_PPU_DMA"))
            dma = None
        elif event == "reveal":
            dma = None
    spans.sort()
    assert waiting is None and all(a[1] <= b[0] for a, b in zip(spans, spans[1:]))
    return spans


def measure(run):
    cpu = json.loads((run / "joint.json").read_bytes())
    assert cpu["passed"] and cpu["last_status"] == 1
    generations = list(range(905,905+cpu["commits"]))
    events = json.loads((run / "events.json").read_bytes())
    rows = window(run)
    reveals = [r for r in rows if r["event"] == "reveal"]
    assert [r["g"] for r in reveals] == generations
    start, end = reveals[1]["clock"], reveals[-1]["clock"]
    ready = {(e["input_generation"], e["index"]): e["ready"] for e in events if e["event"] == "sender652_ready"}
    pops = defaultdict(list)
    release = {}
    prepared = {}
    data_bytes = Counter()
    issued = {e["generation"]:e["clock"] for e in events
              if e.get("opcode")=="0xe1" and e["packet_opcode"]==3}
    capture = [e["capture_ready"] for e in events if e["event"] == "source_begin"]
    assert len(capture) == len(generations)
    skips = []
    for a,b in zip(capture[1:],capture[2:]):
        slots,rem = divmod(b-a,PERIOD)
        assert rem == 0 and slots >= 1
        skips.append(int(slots)-1)
    for e in events:
        if e.get("opcode") == "0xd2":
            pops[e["input_generation"]].append(e["clock"])
        elif e.get("opcode") == "0xea":
            assert e["generation"] not in release
            release[e["generation"]] = e["clock"]
        elif e.get("opcode") == "0xd3":
            assert e["input_generation"] not in prepared
            prepared[e["input_generation"]] = e["start"]
        if e.get("opcode") in ("0xd1","0xe1"):
            g = e.get("input_generation",e["generation"])
            if g >= 907:
                data_bytes[e["opcode"]] += e["bytes"]
    assert sorted(release) == sorted(prepared) == generations
    for f in cpu["frames"]:
        g = f["generation"]
        assert f["ACK_masterclock"] <= release[g]
        if g < generations[-1]:
            assert release[g] <= prepared[g+1]
    wire = packets(run)
    seals = {int.from_bytes(p[8:10], "little"): i for i,p in enumerate(wire, 1) if p[0] == 3}
    assert sorted(seals) == generations
    intervals = consumer_intervals(rows)
    ends = [s[1] for s in intervals]
    counts, costs, overlap = Counter(), Counter(), Counter()
    calls = 0
    prior = None
    total_spi = 0.0
    for e in events:
        if e["event"] not in ("SPI", "observer"):
            continue
        t1 = e["clock"]
        t0 = e["start"] if e["event"] == "SPI" else t1 - 64*CLOCK_MS*1000/2625000
        total_spi += max(0, min(end,t1)-max(start,t0))
        if e["opcode"] != "0xe0":
            continue
        g = e["generation"]
        reply = bytes.fromhex(e["reply"])
        same = prior == (g, reply)
        prior = (g, reply)
        if t0 < start or t1 > end:
            continue
        calls += 1
        if not same:
            continue
        sent, retired = (int.from_bytes(reply[k:k+2], "big") for k in (3,5))
        assert 0 <= sent-retired <= 4
        if retired < seals[g] <= sent:
            # The first unretired head can still precede the SEAL in FIFO order.
            if retired+1 == seals[g]:
                owner = "SEAL_head"
            else:
                owner = "ordinary_ahead_of_SEAL"
        elif sent == retired:
            owner = "empty_progress_set" if reply[2]&8 else "empty_no_progress"
        else:
            owner = "full_queue" if sent-retired == 4 else "partly_occupied_queue"
        counts[owner] += 1
        costs[owner] += t1-t0
        i = bisect_right(ends, t0)
        rest = t1-t0
        while i < len(intervals) and intervals[i][0] < t1:
            a,b,activity = intervals[i]
            ticks = min(t1,b)-max(t0,a)
            overlap[activity] += ticks
            rest -= ticks
            i += 1
        overlap["other_or_uninstrumented"] += rest
        if owner == "SEAL_head":
            n = bisect_right(pops[g+1], t0)
            # Exclude the COMMIT record. Its D3 belongs to the next generation.
            if n < len(pops[g+1])-1 and ready[g+1,n] <= t0:
                counts["SEAL_subset_next_data_ready"] += 1
                costs["SEAL_subset_next_data_ready"] += t1-t0
    subset = "SEAL_subset_next_data_ready"
    repeats = sum(v for k,v in counts.items() if k != subset)
    assert abs(sum(overlap.values()) - sum(v for k,v in costs.items() if k != subset)) < .01
    gaps = [b["frame"]-a["frame"] for a,b in zip(reveals[1:], reveals[2:])]
    before_ack = []
    after_seal = []
    ack_to_ea = []
    for f in cpu["frames"][2:-1]:
        g = f["generation"]
        n = bisect_right(pops[g+1],f["ACK_masterclock"])
        before_ack.append(n)
        after_seal.append(n-bisect_right(pops[g+1],issued[g]))
        ack_to_ea.append((release[g]-f["ACK_masterclock"])/CLOCK_MS)
    return dict(firmware=cpu["firmware_SHA256"], snes=cpu["client_SHA256"], gaps=gaps,
                unused_capture_slots=sum(skips), gap_p95_ms=stats([(b["clock"]-a["clock"])/CLOCK_MS
                    for a,b in zip(reveals[1:],reveals[2:])])["p95"],
                total_vblanks=sum(gaps), elapsed_ms=round((end-start)/CLOCK_MS,3),
                final_ACK=cpu["frames"][-1]["ACK_masterclock"], all_E0=calls, repeated_E0=repeats,
                final_EA=round(release[generations[-1]]), data_wire_B=dict(data_bytes),
                dma_B_including_warmup=cpu["vram_DMA_B"],
                repeats_by_queue_state=dict(counts), repeat_ms_by_queue_state=ms(costs),
                repeat_ms_by_snes_activity=ms(overlap), total_SPI_ms=round(total_spi/CLOCK_MS,3),
                next_D2_before_final_ACK=stats(before_ack), next_D2_after_SEAL_before_ACK=stats(after_seal),
                ACK_to_EA_ms=stats(ack_to_ea))


def ms(ticks):
    return {k:round(v/CLOCK_MS,3) for k,v in sorted(ticks.items())}


def compare(temp, clip, phase, tag):
    prefix = f"nes-tile821-{clip}-jointmirror-p{phase}-"
    ref = temp / (prefix+("848series02" if clip=="before_split" else "848series"))
    run = temp / (prefix+tag)
    a,b = measure(ref),measure(run)
    assert a["snes"] == b["snes"]
    assert len(a["gaps"]) == len(b["gaps"]) == {"demo":60,"opening":60,"before_split":18,"after_split":28}[clip]
    for g in range(905,907+len(a["gaps"])):
        name = f"frame-{g}.rgb"
        assert sha(ref/name) == sha(run/name), (clip,phase,g)
    assert a["data_wire_B"]["0xd1"] == b["data_wire_B"]["0xd1"]
    return dict(reference=a, candidate=b, delta_VBlank=b["total_vblanks"]-a["total_vblanks"],
                identical_ordered_output_packets=packets(ref)==packets(run),
                delta_ACK_ms=round((b["final_ACK"]-a["final_ACK"])/CLOCK_MS,3))


def guards(temp, probe):
    results = [json.loads((temp/f"nes-tile821-demo-jointmirror-p1-849fault-{kind}"/"guard849.json").read_bytes())
               for kind in ("stop","crc","identity")]
    menu = json.loads((probe/"menu.json").read_bytes())
    recovery = json.loads((probe/"stop.json/result.json").read_bytes())
    fw = probe/"link02/src/obj-nes-100/firmware.stm"
    assert menu["firmware"] == recovery["firmware_sha256"] == sha(fw)
    assert recovery["passed"] and recovery["base_restored"] and menu["rows"]["normal"]["released"] == 1
    return dict(injected=results, menu=menu, recovery=recovery, flash_B=fw.stat().st_size)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("tag")
    p.add_argument("out",type=Path)
    p.add_argument("probe",type=Path)
    a = p.parse_args()
    result = {clip:[compare(a.temp,clip,phase,a.tag) for phase in (1,2)]
              for clip in ("demo","opening","before_split","after_split")}
    result["guards"] = guards(a.temp,a.probe)
    for clip in ("demo","opening","before_split","after_split"):
        for phase in result[clip]:
            assert phase["candidate"]["firmware"] == result["guards"]["menu"]["firmware"]
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
