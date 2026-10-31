# SPDX-License-Identifier: MIT
"""Partition MMC509 replay time and bound a reversible map-packet encoding."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
CLOCKS_PER_MS = 21477.272


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_plane(data):
    """Shortest literal/repeat representation. A control byte covers 1..128 bytes."""
    suffix = [b""] * (len(data) + 1)
    for i in reversed(range(len(data))):
        choices = []
        for n in range(1, min(128, len(data) - i) + 1):
            part = data[i:i + n]
            choices.append(bytes([n - 1]) + part + suffix[i + n])
            if n >= 2 and part == part[:1] * n:
                choices.append(bytes([128 + n - 1, part[0]]) + suffix[i + n])
        suffix[i] = min(choices, key=len)
    return suffix[0]


def encode_linear(data):
    """Skip to the next run of three equal bytes, with no search table."""
    out = bytearray()
    cursor = 0

    def repeat_at(i):
        return i + 2 < len(data) and data[i] == data[i + 1] == data[i + 2]

    while cursor < len(data):
        end = cursor + 1
        if repeat_at(cursor):
            while end < len(data) and end - cursor < 128 and data[end] == data[cursor]:
                end += 1
            out.extend([128 + end - cursor - 1, data[cursor]])
        else:
            while end < len(data) and end - cursor < 128 and not repeat_at(end):
                end += 1
            out.append(end - cursor - 1)
            out.extend(data[cursor:end])
        cursor = end
    return bytes(out)


def unpack_map(body):
    if len(body) < 2:
        raise ValueError("Missing span")
    size = int.from_bytes(body[:2], "little")
    if not 0 < size <= 240 or size % 2:
        raise ValueError("Invalid map span")
    cursor = 2
    planes = []
    for _ in range(2):
        plane = bytearray()
        while len(plane) < size // 2:
            if cursor == len(body):
                raise ValueError("Missing run header")
            header = body[cursor]
            cursor += 1
            n = (header & 127) + 1
            used = 1 if header >= 128 else n
            if cursor + used > len(body) or len(plane) + n > size // 2:
                raise ValueError("Run outside plane")
            part = body[cursor:cursor + used]
            plane.extend(part * n if header >= 128 else part)
            cursor += used
        planes.append(plane)
    if cursor != len(body):
        raise ValueError("Trailing data")
    return bytes(byte for pair in zip(*planes) for byte in pair)


def load_packets(folder, command_count):
    packets = []
    for i in range(1, command_count + 1):
        lines = (folder / f"command-{i}.txt").read_text().splitlines()
        if lines[1] == "PUSH":
            packets.append(bytes.fromhex(lines[2]))
    return packets


def measure_map(packets):
    frames = Counter()
    linear = Counter()
    changed = total = saved = body_size = 0
    for packet in packets:
        if packet[:2] != bytes([2, 2]):
            continue
        body = packet[16:]
        assert len(body) == int.from_bytes(packet[12:14], "little") and len(body) % 2 == 0
        packed = len(body).to_bytes(2, "little") + encode_plane(body[::2]) + encode_plane(body[1::2])
        assert unpack_map(packed) == body
        for corrupt in (packed[:-1], packed + b"\0", b"\xff\xff" + packed[2:]):
            try:
                unpack_map(corrupt)
            except ValueError:
                continue
            raise ValueError("Accepted damaged map")
        gain = max(0, len(body) - len(packed))
        generation = int.from_bytes(packet[8:10], "little")
        frames[generation] += gain
        simple = len(body).to_bytes(2, "little") + encode_linear(body[::2]) + encode_linear(body[1::2])
        assert unpack_map(simple) == body and len(simple) >= len(packed)
        linear[generation] += max(0, len(body) - len(simple))
        changed += int(gain > 0)
        total += 1
        saved += gain
        body_size += len(body)
    return dict(packets=total, selected=changed, original_body_B=body_size, saved_B=saved,
                linear_saved_B=sum(linear.values()), linear_later10_B_per_display=mean(linear[g] for g in range(907, 917)),
                by_generation_B=dict(frames), later10_B_per_display=mean(frames[g] for g in range(907, 917)),
                scope="Same packet count, 16-byte header retained, two span bytes charged; encode-time and decode-time unmeasured.")


def measure_source(folder, events):
    from analyze_nes_budget504 import common_generation, decode
    from nes_raw506 import encode

    rows = []
    for g in range(905, 917):
        geometry = folder / f"frame{g}.geometry"
        raw = folder / f"frame{g}.raw"
        original, _, _ = encode(geometry.read_bytes(), raw.read_bytes(), g)
        sizes = [e["bytes"] - 3 for e in events if e.get("opcode") == "0xd1" and e["generation"] == g]
        retirement = [e["bytes"] for e in events if e.get("opcode") == "0xd2" and e["generation"] == g]
        assert list(map(len, original)) == sizes and retirement == [8] * len(sizes)
        records = []
        for packet in original:
            at = 0
            while at < len(packet):
                key = int.from_bytes(packet[at:at + 2], "big")
                kind = key >> 13
                width = 8 if kind == 0 and key & 4096 else (2, 1, 7, 4, 7, 1, 2, 8)[kind]
                record = packet[at:at + 4 + width]
                assert len(record) == 4 + width
                records.append(record)
                at += len(record)
        assert records[-1] == original[-1]
        encoded = common_generation(records[:-1], g) + common_generation(records[-1:], g)
        assert decode(encoded, g) == records
        before = sum(sizes) + 11 * len(original)
        after = sum(map(len, encoded)) + 11 * len(encoded)
        rows.append(dict(generation=g, geometry_SHA256=sha(geometry), raw_SHA256=sha(raw),
                         original_packets=len(original), common_packets=len(encoded), saved_nonquery_B=before - after))
    return dict(frames=rows, later10_B_per_display=mean(r["saved_nonquery_B"] for r in rows[2:]),
                accounting="Body plus D1/D2 framing. D0/other polling savings excluded. COMMIT kept separate.")


def analyze(fixture, replay, data):
    physical = json.loads((ROOT / "analysis/hardware510-mmc509.json").read_text())["runs"][0]
    joint = json.loads((fixture / "joint.json").read_text())
    selected = json.loads((ROOT / "analysis/service509-verification.json").read_text())
    assert sha(fixture / "joint.json") == selected["boot_trace_sensitivity_vs506"]["candidate_SHA256"]
    result = json.loads((replay / "result.json").read_text())
    assert result == json.loads((fixture / "result.json").read_text())
    replies = int((replay / "replies.txt").read_text())
    packets = load_packets(fixture, replies)
    buckets = defaultdict(list)
    with (replay / "trace.csv").open(newline="") as trace:
        for row in csv.DictReader(trace):
            buckets[int(row["index"])].append(row)
    assert set(buckets) == set(range(1, len(packets) + 1))
    events = json.loads((fixture / "events.json").read_text())
    with (replay / "sync-differences.csv").open() as trace:
        corrections = list(csv.DictReader(trace))
    assert [int(row["sequence"]) for row in corrections] == [4463, 7572]
    frames = []
    for frame in result["frames"]:
        generation = frame["generation"]
        end_at = max(e["clock"] for e in events if e["generation"] == generation and e.get("opcode") == "0xe9" and e["event"] == "SPI")
        terms = Counter()
        after_end = Counter()

        def add(name, start, end):
            assert start <= end
            terms[name] += end - start
            after_end[name] += max(0, end - max(end_at, start))

        waits = []
        dma_bytes = 0
        sections = Counter()
        last = frame["release_masterclock"]
        for index, packet in enumerate(packets, start=1):
            if int.from_bytes(packet[8:10], "little") != generation:
                continue
            rows = buckets[index]
            assert all((int(r["generation"]), int(r["op"]), int(r["section"])) ==
                       (generation, packet[0], packet[1]) for r in rows)
            clocks = [int(r["clock"]) for r in rows]
            assert clocks == sorted(clocks) and rows[0]["event"] == "load" and rows[-1]["event"] == "ack"
            begin, ack = clocks[0], clocks[-1]
            assert last <= begin
            add("before_or_between_packets", last, begin)
            last = ack
            if packet[0] != 3:
                kind = "bulk_receive" if packet[0] == 7 else "ordinary_receive"
                add(kind, begin, ack)
                if kind == "ordinary_receive":
                    sections[packet[1]] += ack - begin
                continue
            assert int(rows[-1]["value"]) == 1 and ack == frame["ACK_masterclock"]
            assert end_at < begin
            starts = {}
            spent = 0
            for row in rows:
                name = row["event"]
                tick = int(row["clock"])
                if name in ("validate181", "coverage212", "compact489", "wait169", "dma_start"):
                    assert not starts, (generation, name, starts)
                    starts[name] = tick
                    if name == "wait169":
                        waits.append(int(row["scanline"]))
                    if name == "dma_start":
                        dma_bytes += int(row["value"])
                elif name.endswith("_return") or name == "ppu_last":
                    key = "dma_start" if name == "ppu_last" else name.removesuffix("_return")
                    elapsed = tick - starts.pop(key)
                    assert elapsed > 0
                    add(key, tick - elapsed, tick)
                    spent += elapsed
            assert not starts and spent <= ack - begin
            terms["seal_other"] += ack - begin - spent
            after_end["seal_other"] += ack - begin - spent
        duration = last - frame["release_masterclock"]
        assert last == frame["ACK_masterclock"] and sum(terms.values()) == duration
        assert abs(sum(after_end.values()) - (last - end_at)) < 0.001
        frames.append(dict(end_wire_to_ACK_ms=(last - end_at) / CLOCKS_PER_MS,
                           end_wire_exclusive_ms={k: v / CLOCKS_PER_MS for k, v in after_end.items()},generation=generation, total_ms=duration / CLOCKS_PER_MS,
                           exclusive_ms={k: v / CLOCKS_PER_MS for k, v in terms.items()},
                           ordinary_by_section_ms={k: v / CLOCKS_PER_MS for k, v in sections.items()},
                           seal_PPU_DMA_B=dma_bytes, wait_entry_scanlines=waits))
    keys = set().union(*(f["exclusive_ms"] for f in frames))
    windows = {}
    for name, subset in [("first_two", frames[:2]), ("later_ten", frames[2:])]:
        windows[name] = {k: mean(f["exclusive_ms"].get(k, 0) for f in subset) for k in sorted(keys)}
        windows[name]["end_wire_to_ACK_ms"] = mean(f["end_wire_to_ACK_ms"] for f in subset)
        windows[name]["end_wire_exclusive_ms"] = {k: mean(f["end_wire_exclusive_ms"].get(k, 0) for f in subset)
                                                  for k in sorted(keys)}
        waits = [line for f in subset for line in f["wait_entry_scanlines"]]
        windows[name]["wait_calls"] = len(waits)
        windows[name]["wait_calls_started_in_VBlank"] = sum(line >= 225 for line in waits)
        windows[name]["ordinary_map_section_ms"] = mean(f["ordinary_by_section_ms"].get(2, 0) for f in subset)
        windows[name]["total_ms"] = mean(f["total_ms"] for f in subset)
        windows[name]["seal_packet_ms"] = sum(windows[name][k] for k in
            ("compact489", "validate181", "coverage212", "dma_start", "wait169", "seal_other"))
    wire_B = physical["nonquery_wire_projection_ms"] * 2625 / 8
    e1 = physical["driver_ops_nested"]["E1"]
    count = physical["display"]["completed"]
    required = wire_B - 12 * 2625 / 8
    map_test = measure_map(packets)
    source_test = measure_source(data, events)
    combined = source_test["later10_B_per_display"] + map_test["linear_later10_B_per_display"]
    return dict(experiment=511, merge140="ab55afeefd629bbcc37cbcc57c4d35f1a0172f7e",
                physical_display_FPS=physical["display"]["fps"],
                physical_output_phase_ms=physical["DWT_phases_nested"]["seal_final_ACK"]["ms_per_completed_display"],
                physical_final_ACK_quiet_ms=physical["quiet_nested"]["FINAL_ACK"]["ms_per_completed_display"],
                physical_nonquery_B=wire_B, provisional12ms_remaining_B=required,
                physical_all_E1_framing_B_per_display=19 * e1["calls"] / count,
                physical_dirty_plan_rows=sum(b["mapdirty"] for b in physical["bins"]),
                calendar_SysTick_calls=joint["SysTick_calls"], calendar_ROM_allocations=joint["ROM_read_allocations"],
                matched_frame_count=result["commits"], matched_VRAM_DMA_B=result["vram_DMA_B"],
                reply_count=replies, corrected_status_timestamps=corrections, packets=len(packets), windows=windows, frames=frames,
                map_encoding=map_test, source_common_context=source_test,
                fixture_combined_later10_saved_nonquery_B=combined, fixture_combined_later10_wire_ms=combined * 8 / 2625,
                evidence_SHA256={p.name: sha(p) for p in
                    [fixture / "joint.json", replay / "result.json", replay / "trace.csv", replay / "capture.lua"]},
                limits=["Physical output has no per-PC timestamps. Replay groups are on the 509 boot-calendar workload.",
                        "Elapsed from source release includes earlier work. Wait includes STOP service. DMA goes from trigger to last PPU write.",
                        "Final E9 wire completion to display ACK is a replay bracket. Physical phase starts at nes_sink212_seal and ends when it returns.",
                        "Packet header savings assume unchanged transaction count. Emulator-only map compression is not a measured ARM or SNES speedup."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixture", "replay", "data", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.fixture, args.replay, args.data)
    with args.out.open("x", encoding="utf8", newline="\n") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    print(json.dumps(report["windows"], indent=2))
