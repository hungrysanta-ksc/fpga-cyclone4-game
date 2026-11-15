# SPDX-License-Identifier: MIT
"""Check two complete boots and separate the input deadline from the actual first-blank DMA."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_nes_capture785 import PERIOD, RANGES, csv_groups, ms, one, read, sha
from analyze_nes_first780 import coverage, linked
from prepare_nes_boundary788 import BASE_ELF

LIMIT = 212992
VARIANTS = {"map": "788A", "input": "788B", "joint": "788C", "raster": "788D", "burst": "788E", "map_fit": "788F", "input_fit": "788G", "joint_fit": "788H", "raster_fit": "788I", "burst_fit": "788J", "owner_fit": "788K", "owner_burst_fit": "788L", "owner_map_fit": "788M", "owner_head_fit": "788N", "owner_wait_fit": "788O", "owner_retire_fit": "788P", "owner_split_fit": "788Q"}


def capture_boundary(events, rows, gen, phase):
    prior_ack = one([r for r in rows[gen-1] if r["op"] == 3], "ack")["clock"]
    edge = ((prior_ack - phase) // PERIOD + 1) * PERIOD + phase
    head = one([e for e in events if e.get("generation") == gen], "source_begin")
    wire = [e for e in events if e["event"] == "SPI"]
    pops = [e for e in wire if e["opcode"] == "0xd2" and e.get("input_generation") == gen]
    ready, commit = head["capture_ready"], pops[-1]["clock"]
    start = next(e for e in wire if e["opcode"] == "0xd1" and e.get("input_generation") == gen)["start"]
    assert ready <= start <= commit
    def costs(lo, hi):
        cost = Counter()
        for e in wire:
            overlap = min(hi, e["clock"]) - max(lo, e["start"])
            if overlap > 0:
                cost[e["opcode"]] += overlap
        off_bus = hi - lo - sum(cost.values())
        assert off_bus >= -1
        return dict(SPI_transaction_ms={k:ms(v) for k,v in cost.items()}, outside_SPI_ms=ms(off_bus))
    reads = [e for e in wire if e["opcode"] == "0xd1" and e.get("input_generation") == gen]
    assert len(reads) == len(pops)
    tail = []
    for i in range(max(0,len(reads)-5),len(reads)):
        rd, pop = reads[i], pops[i]
        assert rd["clock"] <= pop["start"] <= pop["clock"]
        tail.append(dict(block=i, D1_start_from_ACK_ms=ms(rd["start"]-prior_ack),
                         D1_end_from_ACK_ms=ms(rd["clock"]-prior_ack),
                         D1_to_D2_start_ms=ms(pop["start"]-rd["clock"]),
                         D2_end_from_ACK_ms=ms(pop["clock"]-prior_ack)))
    return dict(tail=tail, popped_before_ACK=sum(e["clock"]<prior_ack for e in pops),
                total_blocks=len(pops), credit_to_edge_ms=ms(edge-prior_ack), capture_to_first_D1_ms=ms(start-ready),
                capture_to_first_D1=costs(ready,start), D1_to_COMMIT=costs(start,commit),
                last_data_from_ACK_ms=ms(pops[-2]["clock"]-prior_ack),
                final_D2_from_ACK_ms=ms(commit-prior_ack), edge_margin_ms=ms(edge-commit),
                commit_clock=commit)


def packet_order(folder):
    by_generation = {}
    for raw in (folder / "packets.jsonl").read_text().splitlines():
        _, _, header, _ = json.loads(raw)
        h = bytes.fromhex(header)
        g = int.from_bytes(h[8:10], "little")
        by_generation.setdefault(g, []).append((h[0], h[1], h[10:12], h[14:16]))
    return by_generation


def result(folder, base, image, *, group_section5=False):
    s = linked(folder, base, expected_client=image, group_section5=group_section5)
    rows, events = csv_groups(folder / "window.csv"), read(folder / "events.json")
    phase = read(folder / "joint.json")["parameters"]["ROM_phase"]
    def display(g):
        return one([r for r in rows[g] if r["op"] == 3], "reveal")
    s["reveal_vblank"] = {g:display(g)["frame"] for g in range(905,971)}
    s["display_VBlanks"] = {g:s["reveal_vblank"][g]-s["reveal_vblank"][g-1]
                            for g in (909, *range(952,958), 960, 969)}
    s["input"] = {g:capture_boundary(events, rows, g, phase) for g in (951,953,959)}
    s["seal_stages"] = {}
    for g in (931, 934, 951, 952):
        prior = display(g-1)
        seal = one([r for r in rows[g] if r["op"] == 3], "load")
        s["seal_stages"][g] = dict(from_previous_display_ms=ms(seal["clock"]-prior["clock"]),
                                   blank_since_display=seal["frame"]-prior["frame"], line=seal["line"],
                                   to_display_ms=ms(display(g)["clock"]-seal["clock"]))
    s["map_lines"] = [line for kind,off,n,_,blank,line in s["transfers"]
                      if blank == -1 and kind == "map" and
                      any(k == kind and max(off,start) < min(off+n,start+size) for k,start,size in RANGES)]
    early = [e for e in events if e.get("generation")==969]
    enter = one([e for e in early if e.get("offset")==1024], "map_packet_enter")["clock"]
    enqueue = one([e for e in early if e.get("offset")==1024], "map_enqueue")["clock"]
    tx = [e for e in early if e["event"]=="SPI" and enter<=e["start"] and e["clock"]<=enqueue]
    s["first_map"] = dict(enter_to_enqueue_ms=ms(enqueue-enter), ops=[e["opcode"] for e in tx])
    return s


def audit(folder):
    evidence = read(folder / "audit.json")
    assert evidence["frames"] == 66
    rows = csv_groups(folder / "window.csv")
    first = one([r for r in rows[968] if r["op"]==3],"reveal")["frame"]+1
    early = [r for r in rows[969] if r["frame"]==first and r["event"]=="idle524"]
    writes = [r for r in rows[969] if r["frame"]==first and r["event"]=="ppu_dma"]
    tiles = {r["clock"]:r["dst"] for r in csv_groups(folder/"tile532.csv")[969] if r["event"]=="tile"}
    transfers=[]
    for row, write in zip(early,writes,strict=True):
        kind,offset = ("map",row["value"]-65536) if row["value"]>=65536 else ("tile",tiles[row["clock"]])
        transfers.append([kind,offset,write["value"],None,0,write["line"]])
    with (folder/"grants788.csv").open() as stream:
        starts_returns = [r for r in csv.DictReader(stream) if int(r["g"])==969 and int(r["frame"])==first]
    return dict(evidence=evidence, transfers=transfers, target=coverage(transfers,0), beam=starts_returns)


def analyze(temp, probe, modes):
    repo = Path(__file__).resolve().parents[1]
    baseline = read(repo / "analysis/capture785.json")["phases"]
    sources = probe.parent / "nes-handoff787/arm-sealed_poll/src"
    assert sha(sources / "obj-nes-100/sd2snes.elf") == BASE_ELF
    board_client = probe.parent / "nes-complete685/client01/sink165.sfc"
    origin = read(repo / "analysis/arbitrate786.json")["phases"]
    original_target = origin["2"]["map_gapfit"]["edge_after_ACK"]
    builds = {}
    for name, variant in VARIANTS.items():
        src = probe / ("arm-"+name) / "src/obj-nes-100"
        builds[name] = dict(variant=variant, flash=(src/"firmware.stm").stat().st_size,
                            ELF=sha(src/"sd2snes.elf"), firmware=sha(src/"firmware.stm"))
        guard = probe / ("guard-"+name)
        if (guard / "decode.json").is_file():
            for file in ("guards", "credit", "cache", "decode"):
                proof = read(guard / (file+".json"))
                assert (proof["guards"] if file=="guards" else proof)["firmware"] == builds[name]["firmware"]
                builds[name][file] = proof
        if (probe / (name+".json")).exists():
            proof = read(probe / (name+".json"))
            assert proof["firmware"] == builds[name]["firmware"]
            builds[name]["owner"] = proof["cases"]
    phases = {}
    for p in (1,2):
        runs = phases[p] = {}
        ref = temp / f"nes-range778-763-p{p}"
        control_order = packet_order(temp/f"nes-handoff787-sealed_poll-p{p}")
        for mode in ("Q", *modes):
            name = mode.removesuffix("-tile")
            paired = mode.endswith("-tile")
            image = probe / "client/sink165.sfc" if paired else board_client
            if name == "Q":
                folder = temp / f"nes-handoff787-sealed_poll-p{p}"
            else:
                folder = temp / f"nes-boundary788-{mode}-p{p}"
            r = runs[mode] = result(folder, ref, image)
            r["D2_953_advance_vs_786M_ms"] = ms(origin[str(p)]["map_gapfit"]["D2_clock"] - r["input"][953]["commit_clock"])
            order = packet_order(folder)
            if mode == "Q":
                prefix = {}
                for g, packets in order.items():
                    first = next((i for i, packet in enumerate(packets) if packet[:2] == (2, 2)), None)
                    if first is not None:
                        prefix[g] = [(h[1], int.from_bytes(h[3], "little")) for h in packets[:first] if h[0] == 7]
                r["bulk_before_first_map"] = prefix
            assert order.keys() == control_order.keys()
            r["order_changed_from_Q"] = [g for g in sorted(order) if order[g] != control_order[g]]
            if name in builds:
                assert builds[name]["flash"] <= LIMIT and builds[name]["firmware"] == r["firmware"]
                assert "guards" in builds[name]
            else:
                assert r["firmware"] == sha(sources / "obj-nes-100/firmware.stm")
            r["delta_ms"] = {k:dict(dense=round(r["dense_ms"]-base["dense_ms"],6),
                                     ACK970=ms(r["final970"]-base["final970"]))
                             for k,base in baseline[str(p)].items() if k in ("763","783G")}
            checks = dict(protected=all(r["display_VBlanks"][g]==2 for g in (909,953,960,969)),
                          display952=r["display_VBlanks"][952]<=3, display954=r["display_VBlanks"][954]==3,
                          capture953=p==1 or (r["input"][953]["edge_margin_ms"]>0 and
                                               r["input"][953]["commit_clock"]<original_target),
                          map_and_tiles=r["first"]==[n for _,_,n in RANGES] and
                                        bool(r["map_lines"]) and max(r["map_lines"])<=252,
                          dense_and_ACK=all(x<0 for d in r["delta_ms"].values() for x in d.values()))
            r["missed"] = [k for k,v in checks.items() if not v]
            stop = temp / f"nes-boundary788-stop-{mode}-p{p}/proof.json"
            if stop.exists():
                proof = read(stop)
                assert proof["client"]==sha(image) and proof["retained"]==sha(folder/"frame-968.rgb")
                assert proof["commits"]==64 and proof["blanks_after_STOP"]>=3 and proof["map_offset"]==2496 and proof["after_return"]
                r["STOP"] = proof
    timing_pass = [name for name in modes if all(not ph[name]["missed"] for ph in phases.values())]
    data = read(probe / "client/build.json")
    client = {k: data[k] for k in ("reference", "body_sha256", "body_bytes", "body_free",
                                    "physical_free_B", "encoded_B", "prefix_B", "last_latch_line",
                                    "tile_bytes", "new_persistent_WRAM_B")}
    client["image_sha256"] = sha(probe / "client/sink165.sfc")
    return dict(scope="66 cold-boot displays, shared SPI/IRQ and ROM timing model", builds=builds,
                client=client, phases=phases,
                fixed_Q_arrivals={p:audit(temp/f"nes-boundary788-audit-p{p}") for p in (1,2)},
                timing_pass=timing_pass, passing_both=[name for name in timing_pass if all("STOP" in ph[name] for ph in phases.values())])


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("temp","probe","out"):
        p.add_argument(key,type=Path)
    p.add_argument("modes",nargs="+")
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe,a.modes),indent=2)+"\n",newline="\n")
