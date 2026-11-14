# SPDX-License-Identifier: MIT
"""Account for the 958/959 bus and validate linked candidates against two references."""
import argparse
import json
from pathlib import Path

from analyze_nes_capture785 import frame, ms, one, read, sha, csv_groups, PERIOD, RANGES

MODES = ("credit","first","head","firstfit","headfit","finish","drain","service","service_burst","page","release","map_gap","map_gapfit")


def receive(folder):
    events = read(folder / "events.json")
    ready = one([e for e in events if e.get("generation") == 959], "source_begin")
    lo, hi = ready["capture_ready"], ready["clock"]
    assert hi >= lo
    spi = [e for e in events if e["event"] == "SPI"]
    frames = csv_groups(folder / "window.csv")
    ack = one([e for e in frames[958] if e["op"] == 3], "ack")["clock"]
    wire = {}
    previous = lo
    occupied = 0
    # Status sampling, driver entry/exit and cross-clock synchronization
    # enclose the wire. Only charge the physical wire time for complete
    # transfers; a clipped transaction at capture_ready is left unsplit.
    wire_full_ms = 0.0
    clipped_ms = 0.0
    for e in spi:
        begin, end = max(lo,e["start"]), min(hi,e["clock"])
        if begin >= end:
            continue
        assert begin >= previous and e["generation"] == 958
        previous = end
        occupied += end - begin
        if begin == e["start"] and end == e["clock"]:
            wire_full_ms += e["bytes"]*8/2625
        else:
            clipped_ms += ms(end-begin)
        row = wire.setdefault(e["opcode"], {"calls":0, "clocks":0})
        row["calls"] += 1
        row["clocks"] += end - begin
    for row in wire.values():
        row["ms"] = ms(row.pop("clocks"))
    # The driver and wire run inside the charged SPI envelope. The residual
    # includes ARM, IRQ and synchronization. The explicit scan spans are
    # nested within this residual; do not add them again.
    scans = [e for e in events if e["event"] == "scan668" and lo<=e["start"]<=e["clock"]<=hi]
    for e in scans:
        assert not any(s["start"] < e["clock"] and s["clock"] > e["start"] for s in spi)
    source = [e for e in spi if e.get("input_generation")==959]
    pop = [e["clock"] for e in source if e["opcode"]=="0xd2"]
    params = read(folder / "joint.json")["parameters"]
    origin = params["ROM_phase"]
    target = ((ack-origin)//PERIOD+1)*PERIOD+origin
    full_wire = [e for e in spi if e["start"]<pop[-1] and lo<e["clock"]]
    horizon_spi = sum(min(e["clock"],pop[-1])-max(e["start"],lo) for e in full_wire)
    read_pop = [b["start"]-a["clock"] for a,b in zip(full_wire, full_wire[1:])
                if a["opcode"]=="0xd1" and a.get("input_generation")==959
                and b["opcode"]=="0xd2" and b.get("input_generation")==959]
    assert len(read_pop)==len(pop)
    next_ready = one([e for e in events if e.get("generation")==960],"source_begin")["capture_ready"]
    assert next_ready == ((int((pop[-1]-origin)//PERIOD)+1)*PERIOD+origin+240*341*4)
    data_checks = []
    in_959 = [e for e in spi if e.get("input_generation")==959]
    for i,e in enumerate(in_959):
        if e["opcode"]=="0xd2":
            confirm = in_959[i+1]
            assert confirm["opcode"]=="0xd0"
            data_checks.append(confirm["clock"])
    assert len(data_checks)==17
    snapshots = [dict(at_ms=ms(e["clock"]-lo), descriptor=bytes.fromhex(e["reply"])[6],
                      flags=bytes.fromhex(e["reply"])[3]) for e in spi if e["opcode"]=="0xe8"
                 and lo<e["clock"]<=hi and e["generation"]==958]
    prev = one([r for r in frames[959] if r["op"]==3],"reveal")
    seal = one([r for r in frames[960] if r["op"]==3],"load")
    displayed = {g:one([r for r in frames[g] if r["op"]==3],"reveal") for g in (957,958,959,960)}
    display_series = {g:dict(clock=r["clock"],line=r["line"],frame=r["frame"],
                             since957_ms=ms(r["clock"]-displayed[957]["clock"]))
                      for g,r in displayed.items()}
    dma960 = [dict(after_display=r["frame"]-prev["frame"], line=r["line"], bytes=r["value"])
              for r in frames[960] if r["event"]=="ppu_dma"]
    return dict(displays957_960=display_series,ready_clock=lo, receive_clock=hi, ready_to_receive_ms=ms(hi-lo),
                SEAL960_after_display_ms=ms(seal["clock"]-prev["clock"]), DMA960=dma960,
                seal960=[dict(event=r["event"],line=r["line"],after_display=r["frame"]-prev["frame"],
                              since_display_ms=ms(r["clock"]-prev["clock"])) for r in frames[960]
                         if r["op"]==3 and r["event"] in ("load","validate181","coverage212",
                                                         "upload165_entry","wait169","reveal","ack")],
                first_READ_done_ms=ms(next(e["clock"] for e in source if e["opcode"]=="0xd1")-lo),
                SPI=wire, SPI_ms=ms(occupied), complete_wire_ms=round(wire_full_ms,6),
                clipped_transaction_ms=round(clipped_ms,6),
                complete_driver_and_sync_ms=round(ms(occupied)-clipped_ms-wire_full_ms,6),
                non_SPI_ms=ms(hi-lo-occupied),
                scan_calls=len(scans), scan_ms=ms(sum(e["clock"]-e["start"] for e in scans)),
                E8=snapshots, prior_D0_ms=[ms(e["clock"]-lo) for e in spi if e["opcode"]=="0xd0"
                                         and lo<e["clock"]<=hi and e.get("input_generation")==958],
                ready_to_commit_ms=ms(pop[-1]-lo), ready_to_edge_ms=ms(target-lo),
                ready_to_commit_SPI_ms=ms(horizon_spi), read_to_pop_service_ms=ms(sum(read_pop)),
                unchanged_serial_excess_ms=ms(horizon_spi+sum(read_pop)-(target-lo)),
                commit_after_ACK_ms=ms(pop[-1]-ack), ACK_to_edge_ms=ms(target-ack),
                commit_edge_margin_ms=ms(target-pop[-1]), pops_before_ACK=sum(t<=ack for t in pop), confirmed_before_ACK=sum(t<=ack for t in data_checks),
                capture960_before_959_display_ms=ms(one([r for r in frames[959] if r["op"]==3],"reveal")["clock"]-next_ready))


def collect(tmp, probe, runs, overrides=None):
    overrides = overrides or {}
    base = read(Path(__file__).resolve().parents[1] / "analysis/capture785.json")
    result = dict(scope="Same boot and original 65816. SPI envelopes include calibrated driver, clocks and rendezvous; non-SPI residual includes ARM, IRQ and scheduler. No physical FPS measurement.", builds={}, phases={})
    for name in MODES:
        obj = probe / ("arm-"+name) / "src/obj-nes-100"
        result["builds"][name] = dict(flash=(obj/"firmware.stm").stat().st_size,
             firmware=sha(obj/"firmware.stm"), elf=sha(obj/"sd2snes.elf"))
        if name in runs:
            g = probe / ("guard-"+name)
            result["builds"][name]["guards"] = read(g / "guards.json")["guards"]
            result["builds"][name]["cache"] = read(g / "cache.json")
            proofs = ["guards","cache"]
            if name in ("credit","firstfit","headfit","page","map_gapfit"):
                result["builds"][name]["positive_credit"] = read(g / "credit.json")
                proofs.append("positive_credit")
            for proof in proofs:
                assert result["builds"][name][proof]["firmware"] == result["builds"][name]["firmware"]
    for phase in (1,2):
        ph = result["phases"][phase] = {}
        ref = base["phases"][str(phase)]
        for name, folder in (("783G","nes-grant783-window"),("785I","nes-capture785-cache")):
            ph[name] = receive(tmp / f"{folder}-p{phase}")
        for name in runs:
            folder = overrides.get((name,phase),tmp / f"nes-arbitrate786-{name}-p{phase}")
            if name=="page" and phase==1 and not (folder/"joint.json").exists():
                original=tmp/f"nes-arbitrate786-{name}-p{phase}"
                assert original != folder and not (original/"joint.json").exists()
                assert sha(original/"window.csv")==sha(folder/"window.csv")
                location="capture.lua:94: assertion failed!"
                assert all(location in (d/"map-error.txt").read_text() for d in (folder,original))
                beam=read(tmp/"nes-arbitrate786-beam2-page-p1"/"beam.json")
                assert beam["g"]==957
                ph[name]=dict(trace=original.name,repeated_in=folder.name,
                              trace_hash=sha(folder/"window.csv"),last_display=956,
                              beam_guard=beam,missed=["independent_DMA_guard"])
                continue
            s = frame(folder,tmp / f"nes-range778-763-p{phase}")
            assert s["matched_frames"]==66 and s["firmware"]==result["builds"][name]["firmware"]
            s.update(receive(folder))
            s["trace"]=folder.name
            s["relative_ms"] = {k:dict(dense=round(s["dense_ms"]-ref[k]["dense_ms"],6),
                                      ACK970=ms(s["final970"]-ref[k]["final970"])) for k in ("783G","763")}
            protected = (909,960,969)
            gates = dict(displays=s["dense"][1:3]==[2,3], protected=all(s["intervals"][g]==2 for g in protected),
                         DMA=s["first969"]==[n for _,_,n in RANGES] and bool(s["map_start_lines"]) and max(s["map_start_lines"])<=252,
                         time=all(v<0 for delta in s["relative_ms"].values() for v in delta.values()),
                         flash=result["builds"][name]["flash"]<=212992)
            s["missed"]= [key for key in gates if not gates[key]]
            stop = tmp / f"nes-arbitrate786-stop-{name}-p{phase}" / "proof.json"
            if stop.exists():
                proof = read(stop)
                assert proof["map_offset"]==2496 and proof["after_return"] and proof["commits"]==64
                assert proof["blanks_after_STOP"]>=3 and proof["last_packet_status"]==0
                assert proof["retained"]==sha(folder/"frame-968.rgb") and proof["client"]==sha(folder/"client.sfc")
                s["STOP_after_map"] = proof
            ph[name]=s
    result["passing_both"]=[n for n in runs if all(not result["phases"][phase][n]["missed"] for phase in (1,2))]
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("tmp","probe","out"):
        p.add_argument(key,type=Path)
    p.add_argument("runs",nargs="+",choices=MODES)
    p.add_argument("--trace",action="append",nargs=3,default=[],metavar=("MODE","PHASE","PATH"))
    a=p.parse_args()
    a.out.write_text(json.dumps(collect(a.tmp,a.probe,a.runs,{(n,int(p)):Path(d) for n,p,d in a.trace}),indent=2)+"\n", newline="\n")
