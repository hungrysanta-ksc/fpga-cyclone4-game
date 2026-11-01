# SPDX-License-Identifier: MIT
"""Compare uninterrupted runs on one clock. Store metrics and hashes, never ROM data."""
import argparse
import csv
import json
import struct
from itertools import groupby
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from prepare_nes_dense519 import tile_digest, tiles
from run_nes_scroll229 import sha
from test_nes_service509_schedule import Calendar

ROOT = Path(__file__).resolve().parents[1]
HZ = 21477272
LAST = 957


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def ms(clocks):
    return clocks * 1000 / HZ


def consumed_tiles(folder):
    output = {}
    with (folder / "packets.jsonl").open() as f:
        for line in f:
            _, _, record_hex, payload_hex = json.loads(line)
            record = bytes.fromhex(record_hex)
            if record[0] != 7:
                assert not payload_hex
                continue
            payload = bytes.fromhex(payload_hex)
            g, offset = struct.unpack_from("<HH", record, 8)
            size = 32 if record[1] else 16
            assert int.from_bytes(record[14:16], "little") == len(payload) and len(payload) % size == 0
            for i in range(0, len(payload), size):
                key = (g, record[1], offset+i)
                assert key not in output
                output[key] = payload[i:i+size]
    return output


def seal_waits(trace):
    waits = []
    pending = None
    for r in trace:
        if r["op"] != "3":
            continue
        event = r["event"]
        if event == "wait169":
            assert pending is None, "overlapping VBlank waits"
            pending = r
        elif pending and (event.startswith("wait_return_") or event == "final_upload212_same_blank212"):
            waits.append(dict(enter_line=int(pending["line"]), resume_line=int(r["line"]),
                              ms=ms(int(r["clock"])-int(pending["clock"]))))
            pending = None
    assert pending is None, "unclosed VBlank wait"
    return waits


def busy_between(trace, lo, hi):
    # Clip disjoint packet service intervals at both boundaries, including a
    # packet already loaded at lo. Queue-empty gaps have no packet owner.
    started = {}
    service = Counter()
    for r in trace:
        key, tick = r["index"], int(r["clock"])
        if r["event"] == "load":
            assert key not in started
            started[key] = tick
        elif r["event"] == "ack":
            left = max(lo, started.pop(key))
            right = min(hi, tick)
            if right > left:
                service[f'{r["op"]}/{r["section"]}'] += right-left
    assert not started and sum(service.values()) <= hi-lo
    return {k:ms(v) for k, v in service.items()}


def measure(folder, plans, firmware, calendar):
    result = read(folder / "joint.json")
    assert result["passed"] and result["commits"] == result["map_WRAM_VRAM_verified"] == 53
    assert result["firmware_SHA256"] == firmware
    assert result["parameters"]["ROM_phase"] == 0 and result["parameters"]["ROM_calendar"] == calendar.summary
    phase = read(folder / "obj-phases.json")
    events = defaultdict(list)
    for r in read(folder / "events.json"):
        events[r["generation"]].append(r)
    cpu = defaultdict(list)
    with (folder / "window.csv").open() as f:
        for row in csv.DictReader(f):
            cpu[int(row["g"])].append(row)
    rows = []
    assert [r["generation"] for r in result["frames"]] == list(range(905, LAST + 1))
    for g, f in enumerate(result["frames"], 905):
        t, e, p = cpu[g], events[g], phase[str(g)]
        def clock(op, event):
            matches = [int(row["clock"]) for row in t if row["op"] == op and row["event"] == event]
            assert len(matches) == 1, (g, op, event, matches)
            return matches[0]

        ack = clock("3", "ack")
        assert ack == f["ACK_masterclock"]
        final = next(r for r in t if r["op"] == "3" and r["event"] == "ack")
        assert final["value"] == "1" and int(final["line"]) >= 225
        obj = [int(row["clock"]) for row in t if row["op"] == "7" and row["section"] == "1" and row["event"] == "ack"]
        demand = plans[g]
        assert len(p.get("obj_plans", [])) == demand["obj_tiles"]
        assert p.get("obj_rom_reads", 0) == demand["obj_rom_bytes_requested"]
        assert bool(obj) == bool(demand["obj_tiles"])
        seal = clock("3", "seal")
        assert p["end_accepted"] < seal <= ack <= p["ea"]
        source = [r["clock"] for r in e if r["event"] == "source_begin"]
        planner = [r["clock"] for r in e if r["event"] == "planner_enter"]
        assert len(source) == len(planner) == 1
        spi = [r for r in e if r["event"] == "SPI"]
        counts = Counter(r["opcode"] for r in spi)
        row = dict(generation=g, source_begin=source[0], planner_enter=planner[0],
                   end_accepted=p["end_accepted"], seal_entered=seal, display_ack=ack, ea=p["ea"],
                   gap_ms=ms(ack-rows[-1]["display_ack"]) if rows else None, obj_tiles=demand["obj_tiles"],
                   obj_rom_reads=p.get("obj_rom_reads", 0), obj_bulk=len(obj), e8=counts["0xe8"], e9=counts["0xe9"],
                   spi_bytes=sum(r["bytes"] for r in spi), seal_to_ack_ms=ms(ack-seal), seal_waits=seal_waits(t))
        if obj:
            last_rom = p["last_obj_rom_response"]
            last_bulk = obj[-1]
            request = p["first_obj_rom_request"]
            # Earliest possible final response from this same first request, if
            # all OBJ reads were already available and had exclusive access.
            earliest = request
            for _ in range(row["obj_rom_reads"]):
                _, earliest = calendar.select(earliest)
            assert earliest <= last_rom <= last_bulk <= seal
            row.update(first_obj_rom_request=request, first_obj_grant_wait_ms=ms(calendar.select(request)[0]-request),
                       minimum_rom_span_ms=ms(earliest-request), actual_rom_span_ms=ms(last_rom-request))
            slots = sorted(plan["slot"] for plan in p["obj_plans"])
            assert len(slots) == len(set(slots)) and len(slots)*32 <= 2048
            # Lower bound for this workload only, allowing all disjoint OBJ
            # destinations to be ready together; no timing gain is implied.
            spans = 1 + sum(y != x+1 for x, y in zip(slots, slots[1:]))
            assert spans <= len(obj)
            batch_order = []
            for _, batch in groupby(p["obj_plans"], key=lambda plan: plan["accepted_clock"]):
                batch_order.extend(sorted(plan["slot"] for plan in batch))
            batch_spans = 1 + sum(y != x+1 for x,y in zip(batch_order, batch_order[1:]))
            assert spans <= batch_spans
            arrivals = Counter(plan["accepted_clock"] for plan in p["obj_plans"])
            row.update(first_obj_accepted=p["obj_plans"][0]["accepted_clock"],
                       obj_batches=[dict(clock=clock, tiles=count) for clock,count in sorted(arrivals.items())],
                       obj_slot_order=[plan["slot"] for plan in p["obj_plans"]], sorted_obj_spans=spans, sorted_within_e9_spans=batch_spans,
                       obj_bulk_ack_clocks=obj,
                       last_obj_rom=last_rom, last_obj_bulk_ack=last_bulk,
                       last_rom_to_last_bulk_ms=ms(last_bulk-last_rom), last_bulk_to_seal_ms=ms(seal-last_bulk),
                       packet_service_tail_ms=busy_between(t, last_bulk, seal))
        rows.append(row)
    return rows, result


def interval(rows, first, last):
    return mean(r["gap_ms"] for r in rows if first <= r["generation"] <= last)


def analyze(a):
    previous = read(ROOT / "analysis/obj518-verification.json")
    plans = {f["generation"]: f for f in previous["plans"]["frames"]}
    guards = read(a.guards)
    calendar = Calendar(a.calendar)
    variants = {}
    sequences = []
    expected_tiles = tiles(a.fixture, LAST)
    for name, folder in (("baseline", a.baseline), ("candidate", a.candidate)):
        rows, result = measure(folder, plans, guards[name]["sha256"], calendar)
        assert consumed_tiles(folder) == expected_tiles
        sequences.append(rows)
        variants[name] = dict(warm_mean_ms=interval(rows, 907, LAST), dense_mean_ms=interval(rows, 951, 955),
                              parameters=result["parameters"], client_sha256=result["client_SHA256"],
                              instructions=result["ARM_instructions"], irqs=result["SysTick_calls"],
                              rom_reads=result["ROM_read_allocations"], bulk_high_water=result["max_bulk_banks"],
                              wire=result["wire_B"], display_clocks=[r["display_ack"] for r in rows],
                              dense_rows=[r for r in rows if 948 <= r["generation"] <= 957],
                              pins={n:sha(folder/n) for n in ("joint.json", "window.csv", "events.json", "obj-phases.json")})
    b, c = sequences
    base, cand = variants.values()
    assert base["client_sha256"] == cand["client_sha256"] and base["parameters"] == cand["parameters"]
    assert base["parameters"]["start"] == 3000000 and base["parameters"]["ROM_phase"] == 0
    assert base["rom_reads"] == cand["rom_reads"] and max(base["bulk_high_water"], cand["bulk_high_water"]) <= 2
    for r in b[:12]:
        old = previous["matched_schedule"][r["generation"]-905]
        assert old["display_ack"] == r["display_ack"] and old["end_accepted"] == r["end_accepted"]
    for g in range(905, LAST+1):
        assert sha(a.baseline / f"frame-{g}.rgb") == sha(a.candidate / f"frame-{g}.rgb")
    return dict(scope="Same-start, 53 contiguous generations; boot ROM slot replay, not live mapper contention or physical FPS.",
                hardware_test=False, variants=variants, guards=guards,
                interpretation="Compare mean intervals, final ACK clock and individual dense gaps; capture phase may change between generations.",
                delta_final_ms=ms(c[-1]["display_ack"]-b[-1]["display_ack"]),
                delta_dense_mean_ms=cand["dense_mean_ms"]-base["dense_mean_ms"],
                fixture_sha256=sha(a.fixture / "requests.bin"), tile_sha256=tile_digest(expected_tiles), verified_prefix=12, checked_tile_payloads=len(expected_tiles), identical_rgb_frames=len(b))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("baseline", "candidate", "guards", "calendar", "fixture", "out"):
        p.add_argument("--"+key, type=Path, required=True)
    a = p.parse_args()
    a.out.write_text(json.dumps(analyze(a), indent=2) + "\n", encoding="utf8", newline="\n")
