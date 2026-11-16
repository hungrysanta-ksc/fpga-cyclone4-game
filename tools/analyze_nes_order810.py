"""Verify MMC807, CRC809 and the order810 schedules on the same 66 captures."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_output768 import PROBES, csv_groups, one, read, sha, timeline
from analyze_nes_tail735 import section5
from test_nes_raw506_joint import MASTER


def ms(ticks):
    return ticks * 1000 / MASTER


def schedule(folder, reference, expected_client=None):
    joint = read(folder / "joint.json")
    assert joint["passed"] and joint["commits"] == joint["map_WRAM_VRAM_verified"] == 66
    assert joint["parameters"] == reference["parameters"]
    assert joint["client_SHA256"] == (expected_client or reference["client_SHA256"])
    cpu = csv_groups(folder / "window.csv")
    events = read(folder / "events.json")
    packets = [json.loads(line) for line in (folder / "packets.jsonl").read_text().splitlines()]
    reveals = {g:one([r for r in cpu[g] if r["op"]==3], "reveal") for g in range(905,971)}
    r951 = reveals[951]
    early = [r for r in cpu[951] if r["event"]=="ppu_dma" and r["frame"]==r951["frame"]-1
             and r["clock"]<one([v for v in cpu[951] if v["op"]==3],"load")["clock"]]
    # The monitor samples the programmed command shortly before the PPU write.
    # Pair by length and clock rather than assigning DMA type from its length.
    grants = []
    for filename, kind, length in (("budget685.csv","map","bytes"),("tile532.csv","tile","n")):
        with (folder/filename).open() as f:
            for v in csv.DictReader(f):
                if int(v.get("generation",v.get("g")))!=951:
                    continue
                for r in early:
                    if r["value"]==int(v[length]) and 0<=r["clock"]-int(v["clock"])<512:
                        grants.append(dict(kind=kind,bytes=r["value"],line=r["line"],
                                           destination=int(v["dst"]) if kind=="tile" else None))
    map_ack=max(r["clock"] for r in cpu[951] if r["section"]==2 and r["event"]=="ack")
    next_ordinary=next(r for r in cpu[951] if r["event"]=="load" and r["section"] in (3,4,5)
                       and r["clock"]>map_ack)
    map_polls=sum(r.get("opcode")=="0xe0" and map_ack<r["clock"]<next_ordinary["clock"]
                  for r in events if r["generation"]==951)
    frame = 959
    trace = timeline(folder,frame,cpu,events,packets)
    obj = [r for r in cpu[frame] if (r["op"],r["section"])==(7,1)]
    last_obj = max(r["index"] for r in obj)
    obj_ack = one([r for r in obj if r["index"]==last_obj],"ack")
    seal = [r for r in cpu[frame] if r["op"]==3]
    origin = reveals[958]["clock"]
    e9 = max(r["clock"] for r in events if r["generation"]==frame and r.get("opcode")=="0xe9")
    after_obj = [r for r in cpu[frame] if r["event"]=="load" and r["index"]>last_obj and r["op"]!=3]
    previous_ack=joint["frames"][958-905]["ACK_masterclock"]
    prefetched=[r for r in events if r.get("input_generation")==959 and r.get("opcode")=="0xd2"
                and r["clock"]<=previous_ack]
    assert not any(r.get("input_generation")==959 and r.get("opcode")=="0xd3" and
                   r["clock"]<=previous_ack for r in events)
    return dict(firmware=joint["firmware_SHA256"],commits=joint["commits"],DMA=joint["vram_DMA_B"],
                start=joint["parameters"]["start"],rgb_map_checked=66,line951=r951["line"],early951=grants,
                after_map951_E0=map_polls,map_ack_to_ordinary951_ms=ms(next_ordinary["clock"]-map_ack),
                restored951=sum(x["bytes"] for x in grants if x["kind"]=="map")==1536
                            and any(x["destination"]==0 and x["bytes"]==16 for x in grants),
                display959=trace["display_interval_VB"],remaining959=trace["post_SEAL_DMA_bytes"],
                after958_ms=dict(E9=ms(e9-origin),OBJ_ACK=ms(obj_ack["clock"]-origin),
                                 SEAL_load=ms(one(seal,"load")["clock"]-origin)),
                pre_ACK958_blocks=len(prefetched),
                pre_ACK958_idle_ms=ms(previous_ack-prefetched[-1]["clock"]) if prefetched else None,
                after_OBJ_packets=len(after_obj),seal959_line=one(seal,"load")["line"],
                waits959=[r["line"] for r in seal if r["event"]=="wait169"],
                final959_line=one(seal,"final212")["line"],reveal959_line=reveals[959]["line"],
                final959_waits=trace["final_waits"],
                dense_vblank=reveals[970]["frame"]-r951["frame"],dense_ms=ms(reveals[970]["clock"]-r951["clock"]),
                last_ACK=joint["frames"][-1]["ACK_masterclock"],wire_B=joint["wire_B"],
                E0_polls=joint["wire_B"]["0xe0"]//20,total_bus_B=sum(joint["wire_B"].values()),
                intervals={g:reveals[g]["frame"]-reveals[g-1]["frame"] for g in range(906,971)},
                hashes={n:sha(folder/n) for n in ("joint.json","packets.jsonl","events.json","window.csv",
                                                    "seal528.csv","budget685.csv","tile532.csv")})


def compare(temp, labels, *, clients=None):
    results = {}
    for phase in (1,2):
        parent = temp / f"nes-output809-base-p{phase}"
        baseline = read(parent/"joint.json")
        ref_section = section5(parent)
        assert len(ref_section)==66
        rows = {}
        for label in ("base","fold",*labels):
            d = temp / f"nes-output809-{label}-p{phase}"
            assert section5(d)==ref_section
            for g in range(905,971):
                for f in (f"expected-{g}.bin",f"map-{g}.bin",f"frame-{g}.rgb"):
                    assert (parent/f).read_bytes()==(d/f).read_bytes(),(label,phase,g,f)
            row = schedule(d,baseline,(clients or {}).get(label))
            rows[label] = row
            row["vs807_dense_ms"] = row["dense_ms"]-rows["base"]["dense_ms"]
            row["vs807_last_ACK_ms"] = ms(row["last_ACK"]-rows["base"]["last_ACK"])
            row["interval_changes_vs807"]={g:delta for g,n in row["intervals"].items()
                                           if (delta:=n-rows["base"]["intervals"][g])}
            row["target_pass"] = (row["restored951"] and row["line951"]<=246 and row["display959"]==2
                                  and row["dense_vblank"]<rows["base"]["dense_vblank"]
                                  and row["vs807_dense_ms"]<0 and row["vs807_last_ACK_ms"]<0)
        results[phase] = rows
    return results


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("labels",nargs="+")
    args=parser.parse_args()
    result=dict(scope="Linked timed ARM and 65816; common model of SPI, IRQ and ROM grants; "
                      "long-run image separately linked and guard-tested. No physical FPS measurement.",
                phases=compare(args.temp,args.labels),builds={})
    for label in args.labels:
        p=PROBES/("nes-"+label)
        root="final" if label in ("order810c","order810g") else "link"
        result["builds"][label]={}
        for n in (807,808):
            image=p/f"{root}{n}/src/obj-nes-100/firmware.stm"
            data=dict(bytes=image.stat().st_size,flash_free=212992-image.stat().st_size,firmware=sha(image))
            for test in ("check","prefix"):
                evidence=p/f"{test}{n}.json"
                if evidence.exists():
                    data[test]=read(evidence)
            result["builds"][label][n]=data
        assert all(result["phases"][phase][label]["firmware"]==result["builds"][label][807]["firmware"]
                   for phase in (1,2))
    result["qualified"]=[]
    for label,editions in result["builds"].items():
        if all(result["phases"][phase][label]["target_pass"] for phase in (1,2)):
            for build in editions.values():
                assert build["flash_free"]>=0
                assert build["check"]["candidate"]["firmware"]==build["firmware"]
                assert build["check"]["guards"]["ACK"]["corrupt_bits"]==152
                assert build["check"]["object_recovery"]["runtime_consecutive_skips"]==2
                assert build["prefix"]["planar"]["verified_bytes"]==2048
            result["qualified"].append(label)
    result["rejected_replays"]={}
    for label in ("order810d","order810e"):
        for phase in (1,2):
            folder=args.temp/f"nes-output809-{label}-p{phase}"
            log=folder.with_suffix(".log")
            if log.exists() and not (folder/"joint.json").exists():
                last=log.read_text(encoding="utf-8",errors="replace").strip().splitlines()[-1]
                entry=dict(phase=phase,last_error=last,log_sha256=sha(log))
                if (folder/"fault.json").exists():
                    state=read(folder/"fault.json")
                    entry["fault_sha256"]=sha(folder/"fault.json")
                    entry["errors"]={name:bytes.fromhex(s["bytes"])[s["layout"]["error"]]
                                     for name,s in state.items() if "error" in s["layout"]}
                result["rejected_replays"].setdefault(label,[]).append(entry)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
