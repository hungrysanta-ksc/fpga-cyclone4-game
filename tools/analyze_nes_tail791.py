# SPDX-License-Identifier: MIT
"""Reconcile 951 receive/restore/credit with the next capture and the full boot."""
import argparse
import json
from pathlib import Path

from analyze_nes_boundary788 import LIMIT, RANGES, csv_groups, ms, one, read, result, sha
from prepare_nes_tail791 import BASE_ELF, MODES
from check_nes_tail791 import profile


def last_blocks(folder, gen):
    events = read(folder/"events.json")
    rows = csv_groups(folder/"window.csv")
    output = [r for r in rows[gen-1] if r["op"]==3]
    display_ack = one(output, "ack")["clock"]
    seal = one(output, "load")["clock"]
    wire = [e for e in events if e["event"]=="SPI"]
    own = [e for e in wire if e.get("input_generation")==gen]
    blocks = [e for e in own if e["opcode"]=="0xd1"]
    returns = [e for e in own if e["opcode"]=="0xd2"]
    assert len(blocks)==len(returns) and blocks[-1]["bytes"]==15
    tail = []
    for idx in range(len(blocks)-3, len(blocks)):
        rd, pop = blocks[idx], returns[idx]
        confirms = [e for e in own if e["opcode"]=="0xd0" and e["start"]>=pop["clock"]]
        status = confirms[0]
        assert rd["clock"]<=pop["start"]<pop["clock"]<=status["start"]
        tail.append(dict(block=idx+1, D1_wire_B=rd["bytes"],
                         read_start_ms=ms(rd["start"]-display_ack),
                         D1_ms=ms(rd["clock"]-rd["start"]),
                         restore_and_issue_ms=ms(pop["start"]-rd["clock"]),
                         D2_return_ms=ms(pop["clock"]-display_ack),
                         checked_D0_ms=ms(status["clock"]-display_ack)))
    after = gen+1
    previous = one([r for r in rows[gen] if r["op"]==3], "reveal")["clock"]
    next_output = [r for r in rows[after] if r["op"]==3]
    next_events = [e for e in events if e.get("generation")==after]
    first_read = next(e for e in wire if e.get("input_generation")==after and e["opcode"]=="0xd1")
    prepare = next(e for e in own if e["opcode"]=="0xd3")
    available = next(e for e in own if e["opcode"]=="0xd0" and e["start"]>=prepare["clock"])
    assert available["clock"]<=blocks[-1]["start"]
    return dict(prior_display_ACK_clock=display_ack,
                last_data_D2_clock=returns[-2]["clock"],COMMIT_D2_clock=returns[-1]["clock"],
                prior_SEAL_from_ACK_ms=ms(seal-display_ack),tail=tail,
                COMMIT_D3_start_ms=ms(prepare["start"]-display_ack),
                COMMIT_positive_D0_ms=ms(available["clock"]-display_ack),
                next_from_previous_display_ms=dict(
                    capture_ready=ms(one(next_events,"source_begin")["capture_ready"]-previous),
                    D1=ms(first_read["start"]-previous),
                    planner=ms(one(next_events,"planner_enter")["clock"]-previous),
                    SEAL=ms(one(next_output,"load")["clock"]-previous),
                    display=ms(one(next_output,"reveal")["clock"]-previous)))


def analyze(temp, probe):
    root = Path(__file__).resolve().parents[1]
    base = probe.parent/"nes-commit790/link-both/src/obj-nes-100"
    assert sha(base/"sd2snes.elf")==BASE_ELF
    image = probe.parent/"nes-seal789/client/sink165.sfc"
    refs = read(root/"analysis/capture785.json")["phases"]
    controls = read(root/"analysis/commit790.json")["phases"]
    sender = temp/"nes-output768-sender/joint-sender.json"
    blocks = read(sender)
    baseline_profiles = {gen:profile(base.parent,blocks[gen]) for gen in ("951","953","959")}
    links = {}
    for mode in MODES:
        obj = probe/("link-"+mode)/"src/obj-nes-100"
        b = links[mode] = dict(Flash_B=(obj/"firmware.stm").stat().st_size,
                               firmware=sha(obj/"firmware.stm"),ELF=sha(obj/"sd2snes.elf"))
        if b["Flash_B"]<=LIMIT:
            proof = read(probe/(mode+"-guards.json"))
            assert proof["firmware"]==b["firmware"]
            assert len(proof["packed_cases"])==9
            raw_only = mode in ("handoff", "combined")
            both = mode in ("rom_seal", "lane_wait", "lane_mask_seal")
            assert proof["sealed_service"]==dict(empty_geometry=4,
                                                 sealed_geometry=3 if both else 1,
                                                 sealed_raw=3 if raw_only or both else 1)
            for gen, reference in baseline_profiles.items():
                assert [v["receiver"] for v in proof["profiles"][gen]]==[v["receiver"] for v in reference]
            b["ARM_checks"] = proof

    phases = {}
    for ph in ("1", "2"):
        candidates = phases[ph] = {}
        ref = temp/("nes-range778-763-p"+ph)
        for name in ["790C"]+[m for m in MODES if links[m]["Flash_B"]<=LIMIT]:
            mode = "both" if name=="790C" else name
            stem = mode+"-p"+ph
            prefix = "nes-commit790-" if name=="790C" else "nes-tail791-"
            folder = temp/(prefix+stem)
            r = result(folder,ref,image)
            record = candidates[name] = {k:r[k] for k in ("dense_ms","final970","first","map_lines","display_VBlanks","verified","firmware")}
            record["input"] = r["input"]
            record["handoff951"] = last_blocks(folder,951)
            record["handoff953"] = last_blocks(folder,953)
            record["handoff959"] = last_blocks(folder,959)
            record["seal952"] = r["seal_stages"][952]
            record["display_frame"] = {g:r["reveal_vblank"][g] for g in (950,951,952,953,954,959,960,968,969,970)}
            record["delta"] = {}
            for refname, other in (("763",refs[ph]["763"]),("783G",refs[ph]["783G"]),("790C",controls[ph]["both"])):
                record["delta"][refname] = dict(dense_ms=r["dense_ms"]-other["dense_ms"], ACK970_ms=ms(r["final970"]-other["final970"]))
            if name=="790C":
                assert record["delta"]["790C"]==dict(dense_ms=0, ACK970_ms=0)
            else:
                assert record["firmware"]==links[name]["firmware"]
            old=candidates["790C"]["handoff951"]
            record["advance_vs_790C_ms"] = {key:ms(old[key]-record["handoff951"][key])
                                             for key in ("prior_display_ACK_clock","last_data_D2_clock","COMMIT_D2_clock")}
            stop=read(temp/(prefix+"stop-"+stem)/"proof.json")
            assert stop["map_offset"]==2496 and stop["after_return"] and stop["commits"]==64
            assert stop["blanks_after_STOP"]>=3 and stop["client"]==sha(image)
            assert stop["retained"]==sha(folder/"frame-968.rgb")
            record["STOP"]=stop
            intervals=r["display_VBlanks"]
            record["gates"]=dict(capture=r["input"][951]["edge_margin_ms"]>0,
                                 intervals=all(intervals[g]==n for g,n in ((909,2),(952,3),(953,2),(954,3),(960,2),(969,2))),
                                 DMA=r["first"]==[n for _,_,n in RANGES] and bool(r["map_lines"]) and max(r["map_lines"])<=252,
                                 performance=all(x<0 for k in ("763","783G") for x in record["delta"][k].values()))
    return dict(scope="Linked ARM and 789 65816, 905–970 continuous, conservative COMMIT POP capture scheduling",
                base_ELF=BASE_ELF,client=sha(image),sender=sha(sender),
                baseline_profiles=baseline_profiles,builds=links,phases=phases,
                passing=[m for m in phases["1"] if all(all(c[m]["gates"].values()) for c in phases.values())])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ("temp", "probe", "out"):
        parser.add_argument(n,type=Path)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+"\n",newline="\n")
