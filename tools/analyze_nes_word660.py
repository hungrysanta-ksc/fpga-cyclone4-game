"""Bind 660 PSRAM grant order, bulk payloads, CPU replay and fitted board reports."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from analyze_nes_export636 import run as verify_display
from analyze_nes_output615 import csv_groups, ms, one, read
from analyze_nes_sender652 import budget
from check_nes_fault641 import digest, evidence


def bulk_packets(folder):
    result = []
    for line in (folder / "packets.jsonl").read_text().splitlines():
        _, _, packet, payload = json.loads(line)
        p = bytes.fromhex(packet)
        if p[0] == 7:
            result.append((int.from_bytes(p[8:10], "little"), p[1],
                           int.from_bytes(p[10:12], "little"), payload.lower()))
    return result


def board_reports(board):
    out = board / "output_files"
    sta = (out / "board.sta.summary").read_text()
    slack = {k: min(map(float, re.findall(r"Model " + k + r" [^\n]+\nSlack : ([-\d.]+)", sta)))
             for k in ("Setup", "Hold", "Recovery", "Removal", "Minimum Pulse Width")}
    def tsv(name):
        with (board / name).open() as f:
            return list(csv.DictReader(f, delimiter="\t"))
    word = tsv("word660.tsv")
    assert len(word) == 24 and len({(r["bit"], r["corner"]) for r in word}) == 24
    worst = min((r for r in tsv("paths612.tsv") if r["check"] == "setup"), key=lambda r: float(r["slack"]))
    assert float(worst["slack"]) == slack["Setup"]
    return dict(slack_ns=slack, worst=worst, word_CDC_min_slack_ns=min(float(r["slack"]) for r in word),
                ROM_pin_min_ns={p: min(float(r["slack"]) for r in tsv("io612.tsv") if r["port"] == p)
                                for p in ("ROM_OE", "ROM_1CE", "ROM_2CE")},
                pins={n: digest(out / n) for n in ("board.sof", "board.fit.rpt", "board.sta.rpt")})


def run(t, probe):
    old = evidence("record657-verification.json")
    base = t / "nes-record657-board-port"
    cases = {}
    for mode in ("board", "shared", "word", "peer", "pin", "emit", "short03", "owner"):
        b = t / f"nes-word660-{mode}"
        result = budget(b)
        fit = (b / "output_files/board.fit.rpt").read_text()
        result["LAB"] = result["LAB_error"] or list(map(int, re.search(
            r"Total LABs:\s+partially or completely used\s+;\s*(\d+) / (\d+)", fit).groups()))
        guard = t / f"nes-word660-guard-{mode}/vsim.log"
        assert "PASS611" in guard.read_text()
        result["guard"] = digest(guard)
        cases[mode] = result
    board = t / "nes-word660-owner"
    rtl_changes = {p.name: digest(p) for p in board.iterdir() if p.suffix in (".sv", ".v", ".sdc", ".qsf")
                   and (not (base / p.name).exists() or digest(p) != digest(base / p.name))}
    assert cases["owner"]["SOF"] and cases["owner"]["STA"]
    physical = {}
    schedules = {}
    for rtl, mode, hits, build in (("full", "pair", 2168, "board"), ("pin", "word", 2144, "pin"),
                                   ("owner", "emit", 0, "owner")):
        bench = t / f"nes-word660-rtl-{rtl}"
        assert "PASS660" in (bench / "vsim.log").read_text()
        for p in bench.glob("*.sv"):
            if p.name != "tb.sv":
                assert digest(p) == digest(t / f"nes-word660-{build}" / p.name)
        grants = [(int(g), int(addr, 16) - 0x200000) for g, k, addr in
                  (r.split() for r in (bench / "grants.txt").read_text().splitlines()) if k == "0" and int(g) <= 957]
        counts = Counter(g for g, _ in grants)
        assert [counts[954], counts[955]] == [80, 72]
        chunks = []
        tokens = []
        for line in (bench / "chunks.txt").read_text().splitlines():
            g, k, slot, token, payload = line.split()
            chunks.append((int(g), int(k), int(slot) * (32 if int(k) else 16), payload))
            tokens.append(int(token))
        assert len(tokens) == len(set(tokens)) == 121
        assert sum(len(row[-1]) // 2 for row in chunks) == 9072
        physical[rtl] = dict(BG_grants=len(grants), BG954=counts[954], BG955=counts[955], bulk_chunks=len(chunks),
                             payload_B=9072, pins={n: digest(bench / n) for n in
                             ("chunks.txt", "grants.txt", "plans.txt", "tb.sv", "vsim.log")})
        phases = {}
        for n in ("1", "2"):
            f = t / f"nes-word660-{mode}{n}"
            prior = t / f"nes-record657-staged2{n}"
            stats = verify_display(f, t / f"nes-front638-both{n}h", expected_bg_hits=hits)
            assert bulk_packets(f) == chunks == bulk_packets(prior)
            def cache(folder):
                return [(int(g), r) for g, v in read(folder / "obj-phases.json").items() for r in v.get("cache611", [])]
            old_counts = Counter(g for g, r in cache(prior) if r[0] == 0 and r[-1] == "ROM")
            assert [old_counts[954], old_counts[955]] == [160, 144]
            rows = cache(f)
            assert [(g, r[1]) for g, r in rows if r[0] == 0 and r[-1] == "ROM"] == grants
            cpu = csv_groups(f / "window.csv")
            seal, = [e["start"] for e in read(f / "events.json") if e["generation"] == 954 and e.get("packet_opcode") == 3]
            ref = evidence("geometry650-verification.json")["phases"][n]["cases"]["base"]["cost"]
            margin = ref["SEAL_from_953_ms"] - ms(seal - one(cpu[953], "reveal")["clock"])
            assert seal <= ref["SEAL_start"] and margin >= 0.011
            old_phase = old["schedules"]["staged2"][n]
            prev = read(prior / "joint.json")
            assert all(stats["measured"][k] == prev[k] for k in ("firmware_SHA256", "parameters", "client_SHA256"))
            intervals = [stats["rows"][g]["interval_VB"] for g in range(951, 956)]
            assert intervals == [3, 4, 3, 3, 3] and stats["rows"][951]["line"] <= 246
            assert stats["rows"][957]["final_waits"] == 0 and stats["last_ACK"] < old_phase["last_ACK"]
            phases[n] = dict(intervals_VBlank=intervals, seal954_start=seal, relative_margin_ms=margin,
                             absolute_margin_ms=ms(ref["SEAL_start"] - seal), line951=stats["rows"][951]["line"],
                             wait957=stats["rows"][957]["final_waits"], last_ACK=stats["last_ACK"],
                             earlier_than_657_ms=ms(old_phase["last_ACK"] - stats["last_ACK"]),
                             dense_mean_ms=stats["dense_mean_ms"], cache=dict(stats["cache"]), measured=stats["measured"],
                             pins=stats["pins"])
        schedules[mode] = phases
    menu = read(probe / "menu.json")
    assert menu["firmware"] == old["firmware"]
    assert all(row["released"] == row["prepared"] == int(k == "normal") for k, row in menu["rows"].items())
    recovery = {}
    for fault in ("none", "busy", "program", "done", "token"):
        p = probe / f"base-{fault}/result.json"
        r = read(p)
        assert r["passed"] and r["firmware_sha256"] == menu["firmware"]
        assert r["base_restored"] == r["safe_return"] == int(fault == "none")
        recovery[fault] = digest(p)
    return dict(baseline=budget(base), fit=cases, STA=board_reports(board), changed_inputs=rtl_changes,
                physical=physical, schedules=schedules, firmware=menu["firmware"], menu=digest(probe / "menu.json"),
                recovery=recovery, scope="Physical RTL pin+staging bytes and grants bound to separate CPU schedule. "
                "Boot-derived ROM calendar, modeled IRQ/SPI service. No physical trial. Owner setup fails.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for n in ("traces", "probe", "out"):
        p.add_argument("--" + n, type=Path, required=True)
    args = p.parse_args()
    args.out.write_text(json.dumps(run(args.traces, args.probe), indent=2) + "\n", newline="\n")
