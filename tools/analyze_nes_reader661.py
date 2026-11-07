"""Tie the selected fitted RTL to independent pin/SPI regressions and both CPU schedules."""
import argparse
import csv
import json
import re
from pathlib import Path

from analyze_nes_export636 import run as verify
from analyze_nes_output615 import csv_groups, ms, one, read
from analyze_nes_sender652 import budget
from analyze_nes_word660 import board_reports, bulk_packets
from check_nes_fault641 import digest, evidence

MODES = ("counter", "pipe", "decode", "tail", "stream", "index", "launch", "mux", "pack")


def inventory(folder):
    text = (folder / "output_files/board.sta.rpt").read_text()
    return {name.strip(): [int(a), int(b)] for name, a, b in re.findall(
        r"^; ((?:Illegal Clocks|Unconstrained [\w ]+?)\s*);\s*(\d+)\s*;\s*(\d+)\s*;", text, re.M)}


def report(t, probe):
    old = evidence("word660-verification.json")
    base = t / "nes-word660-owner"
    mux = t / "nes-reader661-mux"
    modes = {}
    for mode in MODES:
        folder = t / f"nes-reader661-{mode}"
        cost = budget(folder)
        if cost["LAB_error"]:
            cost["LAB"] = cost["LAB_error"][0]
        else:
            rpt = (folder / "output_files/board.fit.rpt").read_text()
            cost["LAB"] = int(re.search(r"Total LABs:\s+partially or completely used\s+;\s*(\d+)", rpt)[1])
            cost["timing"] = board_reports(folder)
        modes[mode] = cost
    assert modes["mux"]["SOF"] and modes["mux"]["LAB"] <= 963
    paths = list(csv.DictReader((mux / "reader661.tsv").read_text().splitlines(), delimiter="\t"))
    assert len(paths) == 6
    endpoint_min = {k: min(float(r["slack"]) for r in paths if r["group"] == k) for k in ("reader", "miso")}
    summary = (mux / "output_files/board.sta.summary").read_text()
    domain_min = {}
    for label, clk in (("168MHz", 1), ("84MHz", 0)):
        pattern = r"Model Setup '[^'\n]+clk\[" + str(clk) + r"\]'\nSlack : ([-.\d]+)"
        domain_min[label] = min(map(float, re.findall(pattern, summary)))
    assert min(domain_min.values()) > 0 and all(x > 0 for x in modes["mux"]["timing"]["slack_ns"].values())
    assert all(float(v) == 0 for v in re.findall(r"TNS\s+: ([-.\d]+)", summary))
    assert inventory(base) == inventory(mux) and len(inventory(mux)) == 6
    # Each build uses only aliases reported by its own mapper, surrounding
    # SDC rules must remain identical. Include all baseline HDL and ROM inputs.
    changed = {}
    for name in set(evidence("trial613-package.json")["inputs"]) | {"nes_geometry_sender653.sv"}:
        if name == "cdc181.sdc":
            def rules(p):
                return re.sub(r"array set aliases659 \{.*?\n\}\n", "", p.read_text(), flags=re.S)
            assert rules(base / name) == rules(mux / name)
        elif digest(base / name) != digest(mux / name):
            changed[name] = digest(mux / name)
    assert set(changed) == {"nes_native_spi165.sv", "nes_rom_boot.sv", "nes_rom_physical.sv"}
    sender = t / "nes-reader661-index-positive"
    final = t / "nes-reader661-final-rtl"
    guard = t / "nes-reader661-final-guards"
    spi_guard = t / "nes-reader661-index-guard"
    for bench in (sender, final, guard, spi_guard):
        for source in bench.glob("*.sv"):
            if source.name != "tb.sv":
                assert digest(source) == digest(mux / source.name)
        assert "Errors: 0" in (bench / "vsim.log").read_text()
    assert "PASS660 physical" in (final / "vsim.log").read_text()
    assert "PASS611" in (guard / "vsim.log").read_text()
    for b in (sender, spi_guard):
        assert "PASS652" in (b / "vsim.log").read_text()
    miter = t / "nes-reader661-owner-miter"
    ref_reader = (mux / "nes_rom_physical.sv").read_text().replace("module nes_rom_physical #", "module pipe_reader #", 1)
    assert (miter / "pipe_reader.sv").read_text() == ref_reader
    assert (miter / "vsim.log").read_text().count("PASS661") == 3
    for name in ("grants.txt", "chunks.txt", "plans.txt"):
        assert digest(final / name) == old["physical"]["owner"]["pins"][name]
    for b in (sender, t / "nes-reader661-sender"):
        assert digest(b / "sender.json") == digest(t / "nes-record657-rtl-port/sender.json")
    phases = {}
    for n in ("1", "2"):
        replay = t / f"nes-reader661-emit{n}"
        prev = t / f"nes-word660-emit{n}"
        v = verify(replay, t / f"nes-front638-both{n}h", expected_bg_hits=0)
        o = old["schedules"]["emit"][n]
        assert v["measured"] == o["measured"] and v["last_ACK"] == o["last_ACK"]
        assert bulk_packets(replay) == bulk_packets(prev)
        # Same starts, source timing, ROM arbitration, SPI, actual DMA/ACK.
        for name in ("events.json", "window.csv", "packets.jsonl", "obj-phases.json", "seal528.csv"):
            assert digest(replay / name) == digest(prev / name), name
        seal, = [e["start"] for e in read(replay / "events.json") if e["generation"] == 954 and e.get("packet_opcode") == 3]
        ref = evidence("geometry650-verification.json")["phases"][n]["cases"]["base"]["cost"]
        margin = ref["SEAL_from_953_ms"] - ms(seal - one(csv_groups(replay / "window.csv")[953], "reveal")["clock"])
        assert margin == o["relative_margin_ms"] and margin >= 0.011 and seal <= ref["SEAL_start"]
        vb = [v["rows"][g]["interval_VB"] for g in range(951, 956)]
        assert vb == [3, 4, 3, 3, 3] and v["rows"][957]["final_waits"] == 0
        base_ack = evidence("record657-verification.json")["schedules"]["staged2"][n]["last_ACK"]
        phases[n] = dict(intervals=vb, seal_margin_ms=margin, last_ACK=v["last_ACK"], earlier_than_657_ms=ms(base_ack-v["last_ACK"]),
                         line951=v["rows"][951]["line"], wait957=v["rows"][957]["final_waits"],
                         dense_ms=v["dense_mean_ms"], max_bulk_banks=v["measured"]["max_bulk_banks"], pins=v["pins"])
    menu = read(probe / "menu.json")
    assert menu["firmware"] == old["firmware"]
    assert all(r["prepared"] == r["released"] == int(k == "normal") for k, r in menu["rows"].items())
    recovery = {}
    for fault in ("none", "program", "done", "busy", "token"):
        f = probe / f"base-{fault}/result.json"
        r = read(f)
        assert r["passed"] and r["base_restored"] == r["safe_return"] == int(fault == "none")
        assert r["firmware_sha256"] == menu["firmware"]
        recovery[fault] = digest(f)
    physical = {k: old["physical"]["owner"][k] for k in ("BG_grants", "BG954", "BG955", "bulk_chunks", "payload_B")}
    physical["pins"] = {k: digest(final / k) for k in ("tb.sv", "vsim.log", "grants.txt", "chunks.txt", "plans.txt")}
    return dict(boards=modes, domain_min_ns=domain_min, endpoint_min_ns=endpoint_min, coverage=inventory(mux),
                changed=changed, phases=phases, physical=physical,
                pins={p.name: digest(p / "vsim.log") for p in (sender, spi_guard, guard, miter)},
                menu=digest(probe / "menu.json"), recovery=recovery, ARM=old["firmware"],
                scope="Same constrained Cyclone IV board and seed. RTL pins and SPI bound to two CPU replays with the boot ROM calendar. No hardware run.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for key in ("traces", "probe", "out"):
        ap.add_argument("--" + key, type=Path, required=True)
    args = ap.parse_args()
    args.out.write_text(json.dumps(report(args.traces, args.probe), indent=2) + "\n", newline="\n")
