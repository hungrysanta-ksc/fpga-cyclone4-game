# SPDX-License-Identifier: MIT
"""Pair complete MCU/65816 schedules with their matching start and board fit."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_nes_dense519 import ROOT, consumed_tiles, interval, measure, ms, read
from analyze_nes_transfer512 import fpga
from nes_schedule492 import funcs
from prepare_nes_dense519 import tile_digest, tiles
from run_nes_scroll229 import sha
from test_nes_service509_schedule import Calendar


def packet_trace(folder):
    with (folder / "window.csv").open() as f:
        rows = list(csv.DictReader(f))
    packets = [json.loads(line) for line in (folder / "packets.jsonl").read_text().splitlines()]
    loaded, service, keys, repeats = {}, {}, [], Counter()
    for _, _, body, payload in packets:
        raw = bytes.fromhex(body)
        key = (raw[:2] + raw[4:], payload)
        # Lane arbitration may change packet sequence, which occupies bytes 2..3.
        keys.append((key, repeats[key]))
        repeats[key] += 1
    for r in rows:
        i, clk = int(r["index"])-1, int(r["clock"])
        if r["event"] == "load":
            loaded[i] = clk
        elif r["event"] == "ack":
            service[keys[i]] = clk-loaded.pop(i)
    assert not loaded and len(service) == len(packets)
    return rows, packets, keys, service


def prefixes(rows, packets, keys, service, baseline):
    output = []
    for at, r in enumerate(rows):
        if r["event"] != "prefix523":
            continue
        start, end = rows[at+1:at+3]
        assert (start["event"], end["event"]) == ("ppu_dma", "ppu_last")
        assert start["index"] == end["index"] == r["index"]
        assert start["frame"] == end["frame"] == r["frame"]
        i = int(r["index"])-1
        ready = packets[i+1][1]
        issue, finish = int(r["clock"]), int(end["clock"])
        output.append(dict(g=int(r["g"]),index=i+1,cursor=int(r["value"]),bytes=int(start["value"]),
                           issue_line=int(r["line"]),last_line=int(end["line"]),
                           issue_to_last=finish-issue,
                           overlapping_next_ready=max(0,finish-max(ready,issue)),
                           paired_packet_delta=service[keys[i]]-baseline[keys[i]]))
    return output


def verified_visible_dma(rows):
    active = None
    count = 0
    for row in rows:
        if int(row["g"]) == 905:
            continue
        if row["event"] == "ppu_dma":
            assert active is None
            active = row
        elif row["event"] == "ppu_last":
            assert active and active["index"] == row["index"] and active["frame"] == row["frame"]
            assert 225 <= int(active["line"]) <= int(row["line"]) < 262
            active = None
            count += 1
    assert active is None
    return count


def trace_pair(original, candidate, plans, calendar, oracle):
    variants = []
    rows_by_variant = []
    for folder in (original, candidate):
        j = read(folder / "joint.json")
        rows, j = measure(folder, plans, j["firmware_SHA256"], calendar)
        assert j["last_status"] == 1 and j["max_bulk_banks"] <= 2 and consumed_tiles(folder) == oracle
        variants.append(dict(warm_ms=interval(rows,907,957),dense_ms=interval(rows,951,955),
                             last_ack=rows[-1]["display_ack"], ARM_instructions=j["ARM_instructions"],
                             SysTick_calls=j["SysTick_calls"],wire_B=j["wire_B"], VRAM_DMA_B=j["vram_DMA_B"],
                             ROM_reads=j["ROM_read_allocations"],bulk_banks=j["max_bulk_banks"],
                             stack_B=j["observed_stack_B"],firmware=j["firmware_SHA256"],client=j["client_SHA256"],
                             parameters=j["parameters"],pins={n:sha(folder/n) for n in
                             ("joint.json","events.json","obj-phases.json","window.csv","packets.jsonl")}))
        rows_by_variant.append(rows)
    b, c = variants
    for field in ("firmware","parameters","ROM_reads","VRAM_DMA_B"):
        assert b[field] == c[field], field
    for g in range(905,958):
        assert sha(original/f"frame-{g}.rgb") == sha(candidate/f"frame-{g}.rgb"), g
    base_events, _, _, base_service = packet_trace(original)
    events, packets, keys, service = packet_trace(candidate)
    # Comparison includes both packet lanes and actual payload bytes.
    assert set(service) == set(base_service)
    for variant, trace in ((b,base_events),(c,events)):
        variant["visible_DMA_pairs"] = verified_visible_dma(trace)
    issued = prefixes(events, packets, keys, service, base_service)
    by_gen = defaultdict(list)
    for p in issued:
        by_gen[p["g"]].append(p)
    ordinary = Counter()
    in_window = Counter()
    for row in events:
        if row["event"] == "ack" and row["op"] != "3":
            generation = int(row["g"])
            ordinary[generation] += 1
            in_window[generation] += 225 <= int(row["line"]) <= 232
    frames = []
    for old, new in zip(*rows_by_variant):
        g = old["generation"]
        assert g == new["generation"]
        early = by_gen[g]
        frames.append(dict(g=g,old_gap_ms=old["gap_ms"],new_gap_ms=new["gap_ms"],
                           old_ack=old["display_ack"],new_ack=new["display_ack"],
                           old_seal_ms=old["seal_to_ack_ms"],new_seal_ms=new["seal_to_ack_ms"],
                           nonseal_ACK=ordinary[g],nonseal_ACK_line225_232=in_window[g],
                           count=len(early),bytes=sum(p["bytes"] for p in early)))
    return dict(start=b["parameters"]["start"],baseline=b,candidate=c,matched_RGB=53,tiles=len(oracle),
                packets=len(packets),warm_delta_ms=c["warm_ms"]-b["warm_ms"],dense_delta_ms=c["dense_ms"]-b["dense_ms"],
                final_delta_ms=ms(c["last_ack"]-b["last_ack"]),prefixes=issued,frames=frames,
                prefix_packet_service_delta_ms=ms(sum(p["paired_packet_delta"] for p in issued)),
                overlapping_next_ready_ms=ms(sum(p["overlapping_next_ready"] for p in issued)))


def firmware_checks(old_src, new_src, folder, label=b"523"):
    old, new = [src/"obj-nes-100" for src in (old_src,new_src)]
    old_hash, new_hash = [sha(d/"firmware.stm") for d in (old,new)]
    old_functions, new_functions = [funcs(d/"sd2snes.elf") for d in (old,new)]
    assert old_functions == new_functions
    before, after = [(d/"firmware.stm").read_bytes() for d in (old,new)]
    assert len(before) == len(after) == 212992 and before[32:].replace(b"520",label) == after[32:]
    checks = read(folder/"response01/result.json")
    assert checks["passed"] and checks["candidate_SHA256"] == new_hash and checks["baseline_SHA256"] == old_hash
    windows = read(folder/"window01.json")
    assert windows["firmware_SHA256"] == new_hash and [r["displays"] for r in windows["accepted"]] == [2,2]
    recovery = {}
    for fault in ("none","program","done","busy","token"):
        r = read(folder/f"recovery-{fault}/result.json")
        assert r["passed"] and r["firmware_sha256"] == new_hash
        assert r["safe_return"] == r["base_restored"] == int(fault == "none")
        recovery[fault] = r["safe_return"]
    return dict(identical_functions=len(old_functions), linked_bytes=len(after), baseline=old_hash,
                candidate=new_hash, response_cases=len(checks["rows"]), base_return=recovery)


def analyze(a):
    calendar = Calendar(a.calendar)
    plans = {r["generation"]:r for r in read(ROOT/"analysis/obj518-verification.json")["plans"]["frames"]}
    oracle = tiles(a.fixture,957)
    phases = [trace_pair(*pair, plans, calendar, oracle) for pair in zip(a.original, a.candidate)]
    assert [p["start"] for p in phases] == [3000000,3178684]
    ref = read(ROOT/"analysis/window516-verification.json")["boards"]["both"]
    source_files = list(read(a.pins)["board_inputs"]) + ["board.qpf","nominal204.sdc","timing506.tcl"]
    changed = [n for n in source_files if sha(a.reference_board/n) != sha(a.board/n)]
    assert changed == ["sink-program.hex"]
    assert sha(a.board/"sink-program.hex") == sha(a.client/"sink-program.hex")
    assert sha(a.reference_board/"output_files/board.sof") == ref["SOF_SHA256"]
    for phase in phases:
        assert phase["candidate"]["client"] == sha(a.client/"sink165.sfc")
    board = fpga(a.board)
    board["SOF_SHA256"] = sha(a.board/"output_files/board.sof")
    return dict(scope="Closed-loop, two matched starts, actual MCU instructions and 65816, calibrated SPI, replayed boot ROM grants. Hardware baseline MMC520.",
                phases=phases,tiles_SHA256=tile_digest(oracle),guards=read(a.guards),maximum_DMA_edges=read(a.edges),
                board_inputs_compared=len(source_files),changed_board_inputs=changed,
                boards={"MMC520":ref,"prefix523":board},
                client={k:read(a.client/"build.json")[k] for k in
                        ("body_bytes","program_bytes","new_WRAM_B","prefix_last_line","prefix_max_bytes","prefix_per_packet")})


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("original","candidate"):
        p.add_argument("--"+key,type=Path,nargs=2,required=True)
    for key in ("fixture","calendar","board","guards","edges","client","out"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--reference-board",type=Path,required=True)
    p.add_argument("--pins",type=Path,required=True)
    p.add_argument("--label-validation",type=Path,nargs=3,metavar=("OLD_SRC","NEW_SRC","CHECKS"))
    a=p.parse_args()
    report=analyze(a)
    if a.label_validation:
        report["labeled_firmware"]=firmware_checks(*a.label_validation)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8",newline="\n")
