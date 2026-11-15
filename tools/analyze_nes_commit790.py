# SPDX-License-Identifier: MIT
"""Separate the last input block from the preceding display/retirement deadline."""
import argparse
import json
from pathlib import Path
from analyze_nes_boundary788 import LIMIT, PERIOD, RANGES, csv_groups, ms, one, read, result, sha

MODES = ("retire", "ready", "both", "raw_planes", "bridge_retire", "raw_bridge", "fixed", "fixed_retire", "owned", "owned_ready")


def timeline(folder):
    events = read(folder/"events.json")
    window = csv_groups(folder/"window.csv")
    ack = one([r for r in window[952] if r["op"]==3],"ack")["clock"]
    wire = [e for e in events if e["event"]=="SPI"]
    pops = [e for e in wire if e.get("input_generation")==953 and e["opcode"]=="0xd2"]
    commit = pops[-1]
    confirm = next(e for e in wire if e["start"]>=commit["clock"] and e["opcode"]=="0xd0")
    assert confirm["input_generation"]==953
    last = next(e for e in reversed(wire) if e["opcode"]=="0xd1" and e["clock"]<=commit["start"])
    assert last["input_generation"]==953 and last["bytes"]==15
    prepare = next(e for e in wire if e["opcode"]=="0xd3" and e.get("input_generation")==953)
    positive = next(e for e in reversed(wire) if e["clock"]<=last["start"] and e["opcode"]=="0xd0")
    assert prepare["clock"]<=positive["start"] and positive["input_generation"]==953
    phase=read(folder/"joint.json")["parameters"]["ROM_phase"]
    edge=((ack-phase)//PERIOD+1)*PERIOD+phase
    sequence = [dict(op=e["opcode"],B=e["bytes"],start_from_ACK_ms=ms(e["start"]-ack),
                     end_from_ACK_ms=ms(e["clock"]-ack)) for e in wire
                if e["clock"]>=ack and e["start"]<=confirm["start"]]
    occupied = sum(min(e["clock"],commit["clock"])-max(ack,e["start"]) for e in wire
                   if e["clock"]>ack and e["start"]<commit["clock"])
    data = [e for e in wire if e.get("generation")==952 and e["opcode"]=="0xe1"]
    v = [r for r in window[952] if r["event"]=="ppu_dma" and r["op"]==3]
    subsequent = {}
    for gen in (952, 960):
        prior_display = one([r for r in window[gen-1] if r["op"]==3], "reveal")["clock"]
        current_events = [e for e in events if e.get("generation")==gen]
        seal = one([r for r in window[gen] if r["op"]==3], "load")
        subsequent[gen] = dict(
            capture_ready_ms=ms(one(current_events, "source_begin")["capture_ready"]-prior_display),
            planner_enter_ms=ms(one(current_events, "planner_enter")["clock"]-prior_display),
            SEAL_accept_ms=ms(seal["clock"]-prior_display))
    return dict(post_ACK_sequence=sequence, from_previous_display_ms=subsequent,
                # The RTL releases on COMMIT mailbox acceptance after D3.
                # A checked positive D0 means the commit record was already staged.
                # Keep the requested, stricter POP boundary as the pass criterion.
                D3_start_margin_ms=ms(edge-prepare["start"]),
                positive_D0_end_margin_ms=ms(edge-positive["clock"]), data_blocks_before_ACK=sum(p["clock"]<ack for p in pops[:-1]),
                data_blocks=len(pops)-1, D1_ms=ms(last["clock"]-last["start"]),
                ARM_D1_to_D2_ms=ms(commit["start"]-last["clock"]),
                D2_ms=ms(commit["clock"]-commit["start"]),
                D2_to_confirm_ms=ms(confirm["clock"]-commit["clock"]),
                ACK_to_D2_SPI_ms=ms(occupied),ACK_to_D2_non_SPI_ms=ms(commit["clock"]-ack-occupied),
                preceding_E1_packets=len(data),preceding_E1_bytes=sum(e["bytes"] for e in data),
                preceding_SEAL_DMA_B=[r["value"] for r in v],
                preceding_ack_line=one([r for r in window[952] if r["op"]==3],"ack")["line"])


def analyze(temp, probe):
    root=Path(__file__).resolve().parents[1]
    refs=read(root/"analysis/capture785.json")["phases"]
    image=probe.parent/"nes-seal789/client/sink165.sfc"
    builds={}
    for mode in MODES:
        obj=probe/("link-"+mode)/"src/obj-nes-100"
        b=builds[mode]=dict(flash=(obj/"firmware.stm").stat().st_size, ELF=sha(obj/"sd2snes.elf"),
                                firmware=sha(obj/"firmware.stm"))
        if b["flash"]<=LIMIT:
            b["guards"]=read(probe/(mode+"-guards.json"))
            assert b["guards"]["firmware"]==b["firmware"]
    phases={}
    for p in (1,2):
        baseline=temp/f"nes-range778-763-p{p}"
        tests=phases[str(p)]={}
        modes=["789E"]+[m for m,b in builds.items() if b["flash"]<=LIMIT]
        for name in modes:
            stem=f"{name}-p{p}"
            folder=temp/(f"nes-seal789-control_cost-raw-p{p}" if name=="789E" else "nes-commit790-"+stem)
            v=result(folder,baseline,image,group_section5=name in ("fixed","fixed_retire"))
            input953=v["input"][953]
            a=tests[name]={k:v[k] for k in ("display_VBlanks","dense_ms","final970","map_lines","first","verified","firmware")}
            a["input953"]=input953
            a["surrounding_input"]={g:v["input"][g] for g in (951,959)}
            a["absolute_display_frame"]={g:v["reveal_vblank"][g] for g in (951,952,953,954,959,960,969,970)}
            a["turnaround"]=timeline(folder)
            a["delta_ms"]={k:dict(dense=round(v["dense_ms"]-refs[str(p)][k]["dense_ms"],6),
                                   ACK970=ms(v["final970"]-refs[str(p)][k]["final970"])) for k in ("763","783G")}
            d=a["display_VBlanks"]
            a["gates"]=dict(display=all(d[g]==2 for g in (909,953,960,969)) and d[954]==3 and d[952]==3,
                            capture=input953["edge_margin_ms"]>0,
                            DMA=v["first"]==[n for _,_,n in RANGES] and bool(v["map_lines"]) and max(v["map_lines"])<=252,
                            performance=all(n<0 for pair in a["delta_ms"].values() for n in pair.values()))
            if name!="789E":
                assert a["firmware"]==builds[name]["firmware"]
                stop_run="stop2" if name in ("fixed","fixed_retire") else "stop"
                proof=read(temp/f"nes-commit790-{stop_run}-{stem}/proof.json")
                assert proof["after_return"] and proof["map_offset"]==2496 and proof["commits"]==64 and proof["blanks_after_STOP"]>=3
                assert proof["client"]==sha(image) and proof["retained"]==sha(folder/"frame-968.rgb")
                a["STOP"]=proof
    rtl=read(temp/"nes-commit790-rtl01/proof.json")
    board=temp/"nes-bg707-board04"
    for fname, digest in rtl["sha256"].items():
        source=board/fname if (board/fname).is_file() else root/"tests/nes-functional"/fname
        assert sha(source)==digest
    assert 0 < rtl["D3_to_release_ns"] < rtl["D3_to_available_ns"]
    return dict(terminal_RTL=rtl,scope="905-970 linked ARM and 65816, shared SPI/IRQ/ROM timing model",
                client=sha(image),builds=builds,phases=phases,
                passing=[n for n in phases["1"] if all(all(p[n]["gates"].values()) for p in phases.values())])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("temp","probe","out"):parser.add_argument(name,type=Path)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args.temp,args.probe),indent=2)+"\n",newline="\n")
