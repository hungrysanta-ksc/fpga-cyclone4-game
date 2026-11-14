"""Split the 969 replay at the last observed OBJ descriptor, submission and SEAL."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from test_nes_raw506_joint import MASTER


def measure(folder):
    events = json.loads((folder / "events.json").read_bytes())
    packets = (folder / "packets.jsonl").read_text().splitlines()
    with (folder / "window.csv").open() as src:
        cpu = [r for r in csv.DictReader(src) if r["g"] in ("968", "969")]
    def rows(gen, op, action):
        return [r for r in cpu if r["g"] == gen and r["op"] == op and r["event"] == action]
    previous, = rows("968", "3", "ack")
    seal, = rows("969", "3", "load")
    ack, = rows("969", "3", "ack")
    obj = [r for r in rows("969", "7", "load") if r["section"] == "1"][-1]
    index = int(obj["index"])
    _, push, header, payload = json.loads(packets[index-1])
    header = bytes.fromhex(header)
    assert header[:2] == bytes((7,1)) and int.from_bytes(header[8:10],"little") == 969
    token = header[16:20]
    candidates = []
    for e in events:
        if e["generation"] != 969 or e.get("opcode") != "0xe8" or e["clock"] > push:
            continue
        rx = bytes.fromhex(e["reply"])
        if rx[6] and rx[14:18] == token:
            assert rx[1:3] == bytes((0xd7,4)) and rx[7] == 1
            assert rx[8:10] == header[14:16] and rx[10:14] == header[10:12]+header[8:10]
            candidates.append(e)
    tx, = [e for e in events if e["generation"] == 969 and e.get("packet_opcode") == 7 and abs(e["clock"]-push)<=1]
    issue, = [e for e in events if e["generation"] == 969 and e.get("packet_opcode") == 3]
    ticks = [int(previous["clock"]), candidates[0]["clock"], tx["start"], int(obj["clock"]),
             issue["start"], int(seal["clock"]), int(ack["clock"])]
    assert ticks == sorted(ticks)
    after_obj = [e for e in events if e["event"]=="SPI" and ticks[3]<=e["start"]<ticks[4]]
    names = ("previous_ACK_to_first_matching_E8", "E8_to_OBJ_issue", "OBJ_issue_to_load",
             "OBJ_load_to_SEAL_issue", "SEAL_issue_to_load", "SEAL_load_to_final_ACK")
    return dict(master_clocks=ticks, elapsed_ms={k:round((b-a)*1000/MASTER,6) for k,a,b in zip(names,ticks,ticks[1:])},
                obj_bytes=len(bytes.fromhex(payload)),token=int.from_bytes(token,"little"),
                SPI_ms_after_OBJ_load=round(sum(e["clock"]-e["start"] for e in after_obj)*1000/MASTER,6),
                map_sha256=hashlib.sha256((folder/"map-969.bin").read_bytes()).hexdigest(),
                rgb_sha256=hashlib.sha256((folder/"frame-969.rgb").read_bytes()).hexdigest())


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    args=p.parse_args()
    result={}
    for phase in (1,2):
        pair={version:measure(args.temp/f"nes-cost768-{version}-p{phase}-ext") for version in ("763","767")}
        for field in ("obj_bytes","token","map_sha256","rgb_sha256"):
            assert pair["763"][field] == pair["767"][field]
        result[phase]=pair
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
