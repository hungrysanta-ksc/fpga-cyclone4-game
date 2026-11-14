# SPDX-License-Identifier: MIT
"""Align linked ARM row writes and checked credit with actual 65816 accepts and DMA."""
import argparse
import json
from pathlib import Path

from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_prefix777 import ms
from analyze_nes_tail735 import section5


def measure(d, ref, control):
    j = read(d / "joint.json")
    assert j["passed"] and j["commits"] == j["map_WRAM_VRAM_verified"] == 66
    assert j["parameters"] == read(ref / "joint.json")["parameters"]
    assert j["client_SHA256"] == read(ref / "joint.json")["client_SHA256"]
    for g in range(905, 971):
        for name in (f"frame-{g}.rgb", f"expected-{g}.bin", f"map-{g}.bin"):
            assert sha(d / name) == sha(ref / name)
    assert section5(d) == section5(ref)
    if control:
        for file in ("window.csv", "packets.jsonl"):
            assert sha(d / file) == sha(ref / file)
    w = csv_groups(d / "window.csv")
    def seal(g, mark):
        return one([r for r in w[g] if r["op"] == 3], mark)
    def interval(g):
        return seal(g, "reveal")["frame"] - seal(g-1, "reveal")["frame"]
    ev = [e for e in read(d / "events.json") if e.get("generation") == 969]
    start = one(ev, "planner_enter")["clock"]
    stop = one(ev, "bg_map_frozen")["clock"]
    image = bytearray((d / "map-968.bin").read_bytes())
    final = (d / "map-969.bin").read_bytes()
    slots, stores = {}, {}
    for e in ev:
        if not start <= e.get("clock", 0) <= stop:
            continue
        if e["event"] == "slot_used757":
            for bit in range(e["size"] * 8):
                if e["value"] & (1 << bit):
                    slots.setdefault(8 * e["byte"] + bit, e["clock"])
        if e["event"] == "map_store757":
            off = e["offset"]
            old, new = bytes.fromhex(e["old"]), bytes.fromhex(e["new"])
            assert image[off:off+len(old)] == old
            image[off:off+len(old)] = new
            for address in range(off, off+len(old)):
                stores[address] = e["clock"]
    assert slots and any(e["event"] == "slot_used757" for e in ev)
    assert image[1024:1408] == final[1024:1408]
    w969 = w[969]
    first = seal(968, "reveal")["frame"] + 1
    anchor = next(e for e in csv_groups(d / "seal528.csv")[969] if e["event"]=="dma" and e["port"]==4)
    f = seal(969,"reveal")["frame"]
    assert any(r["event"]=="ppu_dma" and r["clock"]==anchor["clock"] and r["frame"]==f for r in w969)
    begin = anchor["clock"]-(anchor["line"]-225)*1364-anchor["h"]+4*(f%2==0 and anchor["line"]>240)
    for n in range(f-1, first-1, -1):
        begin -= 262*1364-4*(n%2==0)
    close = begin+22*1364-4*(first%2==0)
    rel = lambda t: ms(t-close) if t is not None else None
    wire = [e for e in ev if e.get("opcode")=="0xe1"]
    accepted = [r for r in w969 if r["event"]=="load"]
    ps = [json.loads(s) for s in (d/"packets.jsonl").read_text().splitlines()]
    details = {}
    for r, tx in zip(accepted, wire, strict=True):
        h = bytes.fromhex(ps[r["index"]-1][2])
        off = int.from_bytes(h[10:12],"little")
        if h[1]!=2 or off not in (1024,1216):
            continue
        assert h[16:]==final[off:off+192] and abs(tx["clock"]-ps[r["index"]-1][1])<=1
        rows = []
        for at in range(off,off+192,64):
            words = {a & ~1 for a in stores if at<=a<at+64}
            times = {a:slots[int.from_bytes(final[a:a+2],"little")&1023] for a in words}
            assert all(t<=max(stores.get(a,0),stores.get(a+1,0)) for a,t in times.items())
            rows.append(dict(row=at//64,written_words=len(words),
                             required_slot=rel(max(times.values(), default=None)),
                             last_store=rel(max((t for a,t in stores.items() if at<=a<at+64),default=None))))
        details[off] = dict(rows=rows, E1=rel(tx["start"]), PUSH=rel(tx["clock"]),
                            load=rel(r["clock"]), ACK=rel(one([a for a in w969 if a["index"]==r["index"]],"ack")["clock"]))
    offers = []
    for i,e in enumerate(ev):
        if e["event"]!="bg684_enter":
            continue
        attempt=next((x for x in ev[i+1:] if x["event"] in ("bg684_enter","bg_map_frozen","map_credit_attempt")),None)
        at=e["clock"]
        e0=next((x for x in reversed(ev[:i]) if x.get("opcode")=="0xe0"),None)
        offers.append(dict(cursor=e["map_next"],final=e["final"],pair=e["pair"],at=rel(at),
                           cached=attempt["outstanding"] if attempt and attempt["event"]=="map_credit_attempt" else None,
                           actual=sum(t["clock"]<=at for t in wire)-sum(r["clock"]<=at for r in w969 if r["event"]=="ack"),
                           last_status=rel(e0["clock"]) if e0 else None))
    output=one(ev,"output_enter531")["clock"]
    limit=seal(969,"load")["clock"]
    selects=[r for r in w969 if r["event"]=="idle524" and r["clock"]<limit]
    starts=[r for r in w969 if r["event"]=="ppu_dma" and r["clock"]<limit]
    tile = {r["clock"]:r["dst"] for r in csv_groups(d/"tile532.csv").get(969,[]) if r["event"]=="tile"}
    transfers=[]
    for sel, dma in zip(selects,starts,strict=True):
        assert 0<dma["clock"]-sel["clock"]<1000
        transfers.append(dict(blank=dma["frame"]-first+1,line=dma["line"],selector=sel["value"],
                              bytes=dma["value"],after_output=dma["clock"]>output,
                              source=(["map",sel["value"]-65536] if sel["value"]>=65536 else ["tile",tile[sel["clock"]]])))
    prior = csv_groups(ref/"window.csv")
    delta_ref = {}
    for g in (909,960,969):
        reference = lambda n: one([r for r in prior[n] if r["op"]==3],"reveal")["frame"]
        delta_ref[g] = interval(g) - (reference(g) - reference(g-1))
    def contents(packets):
        payloads = []
        for _, _, h, tile_data in packets:
            head = bytes.fromhex(h)
            if head[8:10] == (969).to_bytes(2,"little"):
                payloads.append((head[:2]+head[4:],tile_data))
        return sorted(payloads)
    assert contents(ps)==contents(json.loads(s) for s in (ref/"packets.jsonl").read_text().splitlines())
    return dict(interval_delta_vs_parent=delta_ref,verified=66,flash_sha=j["firmware_SHA256"],first_end246=close, rows=details,offers=offers,
                output_pre_B=sum(t["bytes"] for t in transfers if t["after_output"]),DMA=transfers,
                intervals={g:interval(g) for g in (909,960,969)},ACK969=seal(969,"ack")["clock"],
                ACK970=seal(970,"ack")["clock"],SEAL_vs_second_end246_ms=ms(limit-close-(262*1364-4*(first%2==0))),
                dense_ms=ms((seal(957,"reveal")["clock"]-seal(951,"reveal")["clock"])/6),
                events=sha(d/"events.json"))


def analyze(temp, probe):
    phases={}
    for p in (1,2):
        phase=phases[p]={}
        for name in ("763","767","credit","rows"):
            ref=temp/f"nes-cost768-{'763' if name=='763' else '767'}-p{p}-ext"
            phase[name]=measure(temp/f"nes-range778-{name}-p{p}",ref,name in ("763","767"))
        original = {(tuple(t["source"]),t["bytes"]) for t in phase["767"]["DMA"] if t["after_output"]}
        assert sum(n for _,n in original)==496
        for name in ("763","767","credit","rows"):
            done = phase[name]["DMA"]
            phase[name]["original_pre_ranges_completed_B"] = sum(
                length for (kind,off),length in original if any(
                    d["source"][0]==kind and d["source"][1]<=off and
                    off+length<=d["source"][1]+d["bytes"] for d in done))
        phase["receiver_floor"]={k:read(temp/f"nes-range778-floor-{k}-p{p}"/"audit.json") for k in ("one","pair","763","causal","causal763")}
    stop_folder = temp/"nes-range778-stop-ref04"
    stop = read(stop_folder/"result.json")
    stop.update(map_offset=1216, retained=sha(stop_folder/"retained.rgb"))
    assert stop["commits"] == 64 and stop["blanks_after_STOP"] >= 3
    assert stop["retained"] == sha(temp/"nes-range778-767-p1/frame-968.rgb")
    return dict(phases=phases,firmware_B={i:(probe/i/"src/obj-nes-100/firmware.stm").stat().st_size for i in ("arm01","arm02")},
                guards={i:read(probe/i) for i in ("guards.json","guardsB.json")},stop=stop)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","probe","out"):
        parser.add_argument(k,type=Path)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+"\n",encoding="utf8")
