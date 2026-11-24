"""Test the 907 page reservation on the recorded, empty-capture MMC966 schedule."""
import argparse
import json
import struct
from pathlib import Path
from unittest.mock import patch

import nes_page963
from analyze_nes_obj967 import capture
from check_nes_blank959 import directory, read, rows as csv_rows, sha
from nes_feedback953 import evidence
from nes_verified965 import run
from package_nes_trial966 import ROOT, WORK
from test_nes_service509_schedule import Calendar


def unused_slots(temp, reference, trace):
    events = read(reference / "events.json")
    eb, = (e for e in events if e.get("opcode") == "0xeb" and e["generation"] == 907)
    start = trace["confirmed"]
    length = eb["clock"] - eb["start"]
    for e in events:
        if "start" not in e or e["clock"] <= start:
            continue
        if start + length <= e["start"]:
            break
        start = max(start, e["clock"])
    after = start + length
    prior = [json.loads(line) for line in (reference / "producer.jsonl").read_text().splitlines()]
    last = max(row["producer"] for row in prior if row["generation"] == 906)
    assert last < trace["confirmed"] and after < trace["previous_EA_complete"]
    occupied = {v[3] for v in read(reference / "grants904.json")}
    for path in ("ahead911.json", "companion952.json"):
        occupied.update(v[2] for v in read(reference / path))
    occupied.update(v[2] for v in read(reference / "hint963.json")["fills"])
    cal = Calendar(temp / "nes-service509-rom03")
    slots = []
    at = after + 3
    while True:
        grant, reply = cal.select(at)
        if reply >= trace["previous_EA_complete"]:
            break
        if grant not in occupied:
            slots.append((grant, reply))
        at = reply + 1
    return slots, dict(last_906_tile=last, address_confirmed=trace["confirmed"],
                       spi_gap_start=round(start), spi_gap_end=round(after), unused=len(slots))


def rank_rows(path):
    geometry = path.read_bytes()
    count, = struct.unpack_from("<H", geometry, 5732)
    assert len(geometry) == 5741 and count <= 128
    objects = struct.unpack_from(f"<{count}Q", geometry, 2*1056+224)
    # Only the first two distinct rank-zero tags, using masks already in the input.
    tags = {}
    for obj in objects:
        tag, mask, rank = obj&8191, (obj>>38)&255, (obj>>46)&7
        if rank == 0 and (tag in tags or len(tags)<2):
            tags[tag] = tags.get(tag, 0) | mask
    return [16*tag+row for tag, mask in tags.items() for row in range(8) if mask & (1<<row)]


def replay(temp, phase, mode, label):
    reference = directory(temp, phase, "966release", "cold")
    trace, = (r for r in read(ROOT/"analysis/page968-results.json")[str(phase)] if r["generation"] == 907)
    slots, status = unused_slots(temp, reference, trace)
    base = trace["tag"]
    addresses = (rank_rows(temp/"nes-gap904/data-obj/obj/frame907.geometry") if mode.startswith("rank")
                 else [16*tag+row for tag in range(base,base+8) for row in range(8)])
    reserve = mode not in ("control", "retain")
    log = []
    fills = {}
    reserved = {}
    retained = []
    original = nes_page963.page_reader

    def reader(*args):
        class Observed(original(*args)):
            def accept(self, tx, at):
                if tx[0] == 0xea and self.generation == 906 and mode != "control":
                    assert not self.stopped and round(at) == trace["previous_EA_complete"]
                    assert self.free < slots[0][0] and not fills
                    # Commit the completed reads in time order at the lease boundary.
                    # No 906 tile uses the RAM or ROM during this interval.
                    available = iter(slots)
                    for addr in (addresses if reserve else ()):
                        if addr in self.store:
                            continue
                        grant, reply = next(available)
                        self.store[addr] = (reply, self.chr[addr], self.chr[addr+8])
                        fills[addr] = grant
                        self.free = reply + 1
                    if mode in ("retain","page_retain"):
                        reserved.update(self.store)
                    else:
                        reserved.update({a:self.store[a] for a in addresses})
                return super().accept(tx, at)

            def begin(self):
                previous = self.owner
                super().begin()
                if previous == 906 and self.owner == 907 and reserved:
                    retained.append(sum(self.store.get(a) == pair for a, pair in reserved.items()))
                    if mode.endswith(("_keep","retain")):
                        # Upper bound: make only the reserved row pairs visible again
                        # after the ordinary scrub; no restoration bandwidth charged.
                        for addr, pair in reserved.items():
                            self.store[addr] = pair

            def cancel_supply(self):
                reserved.clear()
                return super().cancel_supply()

            def next_rom(self, at):
                if self.generation != 907:
                    return super().next_rom(at)
                kind, addr = self.pending[0]
                n = len(self.grants)
                result = super().next_rom(at)
                if kind == 1 and not addr & 8:
                    log.append((addr, self.grants[n][3] if len(self.grants) > n else None))
                return result
        return Observed

    tail = evidence(directory(temp, 1, "965wire5", "cold"), 910, log_name="mail964.log") if phase == 1 else None
    tag = label + mode
    with patch.object(nes_page963, "page_reader", reader):
        run(temp, phase, "cold", read(ROOT/"analysis/credit965-wire.json")[str(phase)],
            tail=tail, work=WORK, edition=966, tag=tag)
    out = directory(temp, phase, tag, "cold")
    result = read(out/"joint.json")
    assert result["passed"] and result["commits"] == 8
    for gen in range(905, 913):
        assert sha(out/f"frame-{gen}.rgb") == sha(reference/f"frame-{gen}.rgb")
    if mode == "control":
        for name in ("events.json", "producer.jsonl", "window.csv", "records.bin"):
            assert sha(out/name) == sha(reference/name)
    rows = [json.loads(line) for line in (out/"producer.jsonl").read_text().splitlines()]
    first = next(((addr, at) for addr, at in log if at is not None), (None, None))
    ready = max(row["producer"] for row in rows if row["generation"] == 907)
    granted = [at for addr, at in log if at is not None and base <= addr//16 < base+8]
    status.update(filled=len(fills), used_page_row_addresses=len({a for a,_ in log if base<=a//16<base+8}),
                  page_demand_grants=len(granted), first_demand_tag=None if first[0] is None else first[0]//16,
                  first_demand_grant=first[1], reserved_rows_at_handoff=retained,
                  tile907_ready=ready, ACKs={r["generation"]:r["ACK_masterclock"] for r in result["frames"]},
                  distinct_grant_clocks=len(set(fills.values())), display_frame_numbers=[])
    status["display_frame_numbers"] = [int(r["frame"]) for r in csv_rows(out/"window.csv") if r["event"]=="reveal"]
    return status


def report(temp, data, tag):
    release = {}
    logs = temp / "nes-obj967"
    assert "PASS963 SPI" in (logs / "guards.log").read_text(errors="replace")
    for action, after in (("empty", 128), ("sampled", 0), ("stop", 0)):
        line = f"PASS969 action={action} before=128 after={after} grants=128"
        assert line in (logs / f"release969-{action}.log").read_text(errors="replace")
        release[action] = {"before": 128, "after": after, "grants": 128}
    for phase, modes in data.items():
        for mode, result in modes.items():
            if mode not in ("page_keep", "rank_keep", "retain", "page_retain"):
                result.pop("reserved_rows_at_handoff", None)
            path = directory(temp, int(phase), tag + mode, "cold")
            window = [r for r in csv_rows(path / "window.csv") if r["g"] == "907"]
            end = [r for r in window if r["op"] == "3"]
            result["output907"] = {
                event: int(next(r["clock"] for r in end if r["event"] == event))
                for event in ("load", "seal", "upload165_entry", "wait169", "wait_return_5781", "reveal", "ack")
            }
            result["output907"]["last_dma_byte"] = max(int(r["clock"]) for r in end if r["event"] == "ppu_last")
            oam = [r for r in window if r["section"] == "4" and r["op"] == "8"]
            result["output907"]["oam_reuse_service"] = (
                int(next(r["clock"] for r in oam if r["event"] == "ack"))
                - int(next(r["clock"] for r in oam if r["event"] == "load"))
            )
    return {"released_rtl": release, "phases": data}


def physical_pair(folder):
    from read_nes_supply905 import decode
    keys = ("BG", "OBJ", "map", "tiles", "chunks", "last_kind", "last_bytes", "last_offset")
    groups = []
    for edition in (955, 966):
        capture(folder, edition)  # Pins the file digest and checks for missing/invalid records.
        groups.append([r for r in decode(folder / f"nes-frame-mmc{edition}.bin", edition)["rows"] if "last_bytes" in r])

    def matches(a, b):
        return abs(a["tick"] - b["tick"]) <= 30 and all(a[k] == b[k] for k in keys)

    pairs = []
    for a in groups[0]:
        candidates = [b for b in groups[1] if matches(a, b)]
        if len(candidates) == 1 and sum(matches(x, candidates[0]) for x in groups[0]) == 1:
            pairs.append((a, candidates[0]))
    a, b = max(pairs, key=lambda p: (p[0]["E9_to_last_publish_ms"] - p[1]["E9_to_last_publish_ms"])
               - (p[0]["input_to_final_ACK_ms"] - p[1]["input_to_final_ACK_ms"]))
    fields = ("tick", "generation", "input_to_first_E9_ms_bounds", "E9_to_last_publish_ms", "input_to_final_ACK_ms")
    return {"matched": len(pairs), "workload": {k: a[k] for k in keys},
            "955": {k: a[k] for k in fields}, "966": {k: b[k] for k in fields}}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--tag", default="969reserve")
    p.add_argument("--hardware", type=Path, help="directory with the MMC955 and MMC966 physical frame BINs")
    modes = ("control","page","rank","page_keep","rank_keep","retain","page_retain")
    p.add_argument("--modes", nargs="+", choices=modes, default=modes)
    args = p.parse_args()
    data = {}
    for phase in (1, 2):
        data[phase] = {name: replay(args.temp, phase, name, args.tag) for name in args.modes}
    result = report(args.temp, data, args.tag)
    if args.hardware:
        result["hardware_pair"] = physical_pair(args.hardware)
    args.output.write_bytes((json.dumps(result, indent=2)+"\n").encode())
