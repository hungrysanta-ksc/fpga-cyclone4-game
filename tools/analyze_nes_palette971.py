"""Compare the linked ARM candidates on the same modeled ROM calendar."""
import argparse
import json
from pathlib import Path

from check_nes_blank959 import directory, read, rows, sha
from check_nes_output970 import replay
from nes_palette971 import BASE, DIRECT, PAIR, WORK
from test_nes_banks557 import MASTER


def commands(folder, target):
    result = []
    for line in (folder / "packets.jsonl").read_text().splitlines():
        _, at, wire, bulk = json.loads(line)
        head = bytes.fromhex(wire)
        generation = int.from_bytes(head[8:10], "little")
        if generation > target:
            break
        result.append((generation, head[0], at, wire, bulk, 0, 0))
    return result


def measure(folder, control):
    joint = read(folder / "joint.json")
    assert joint["passed"] and joint["commits"] == 8
    reveals = [r for r in rows(folder / "window.csv") if r["event"] == "reveal"]
    assert [int(r["g"]) for r in reveals] == list(range(905, 913))
    for gen in range(905, 913):
        name = f"frame-{gen}.rgb"
        assert sha(folder / name) == sha(control / name)
    events = read(folder / "events.json")
    sends = [e for e in events if e.get("opcode") == "0xe1"]
    packet_rows = []
    for (gen, op, at, wire, *_), event in zip(commands(folder, 912), sends, strict=True):
        assert gen == event["generation"] and op == event["packet_opcode"] and abs(at-event["clock"]) < 1
        if gen == 911:
            head = bytes.fromhex(wire)
            packet_rows.append(dict(op=op, section=head[1], offset=int.from_bytes(head[10:12], "little"),
                                    issue=round(event["start"]), arrive=at))
    begin = packet_rows[0]["issue"]
    def elapsed(op, section):
        return round((next(p["issue"] for p in packet_rows if (p["op"],p["section"]) == (op,section))-begin)*1000/MASTER, 3)
    e9, = (e for e in events if e.get("opcode")=="0xe9" and e["generation"]==911)
    tiles = [r for r in map(json.loads,(folder/"producer.jsonl").read_text().splitlines()) if r["generation"]==911]
    return dict(reveal_vblank=[int(r["frame"]) for r in reveals], ack912=joint["frames"][-1]["ACK_masterclock"],
                plan_issue_after_begin_ms=round((e9["start"]-begin)*1000/MASTER,3), tiles911=tiles,
                palette_after_begin_ms=elapsed(2,3), first_tile_after_begin_ms=elapsed(7,0),
                rgb_matches=8, arm_sha256=joint["firmware_SHA256"], client_sha256=joint["client_SHA256"],
                packets911=packet_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--guard", choices=("bad_seal", "stop_decode"))
    parser.add_argument("--candidate", choices=("direct","pair"), default="direct")
    args = parser.parse_args()
    if args.guard:
        folder = directory(args.temp, 1, "971"+args.candidate, "cold")
        result = replay(args.temp, folder, args.out, "control", commands(folder,911), 911, args.guard)
        (args.out/"guard971.json").write_text(json.dumps(result,indent=2))
        return
    result = {"flash_limit":212992, "flash_bytes":{}, "phase":{}, "guards":{}}
    for name,work in (("control",BASE),("early",WORK),("direct",DIRECT),("pair",PAIR)):
        binary, = (work / "link").rglob("firmware.stm")
        result["flash_bytes"][name] = binary.stat().st_size
        assert binary.stat().st_size <= result["flash_limit"]
    for phase in (1,2):
        control = directory(args.temp, phase, "971control", "cold")
        items = result["phase"][phase] = {}
        items["original_buffer_samples"] = read(args.temp/f"nes-ready971-p{phase}.json")
        for mode in ("966release","971control","971direct","971pair"):
            folder = directory(args.temp, phase, mode, "cold")
            items[mode] = measure(folder,control)
        for mode in ("971direct","971pair"):
            m = items[mode]
            m["ack_delay_vs_control_ms"] = round((m["ack912"]-items["971control"]["ack912"])*1000/MASTER,3)
        negative = directory(args.temp, phase, "971early","cold")
        assert (negative/"fault.json").is_file() and not (negative/"joint.json").exists()
        items["ordinary_span_completed_screens"] = len(list(negative.glob("frame-*.rgb")))
    for variant in ("direct","pair"):
        result["guards"][variant] = {fault:read(args.temp/f"nes-971-{variant}-{fault}"/"guard971.json")
                                     for fault in ("bad_seal","stop_decode")}
    args.out.write_text(json.dumps(result,indent=2)+"\n")


if __name__ == "__main__":
    main()
