"""Compare physical 1034/1035 runs at the same no-input Kirby demo tick."""
import argparse
import hashlib
import json
from pathlib import Path

from read_nes_kirby1034 import decode, MS, ROW, HEADER, INGRESS, OFFSET


def measure(folder, edition, run):
    files = {key: folder / f"nes-{key}-mmc{edition}-{run}차.{ext}" for key, ext in
             (("frame", "bin"), ("budget", "txt"), ("progress", "txt"), ("game-last", "txt"))}
    logs = {key: dict(line.split("=", 1) for line in path.read_text(encoding="utf-8-sig").splitlines()
                      if "=" in line) for key, path in files.items() if key in ("budget", "game-last")}
    raw = files["frame"].read_bytes()
    rows = decode(raw, edition)["rows"]
    [(i, row)] = [(i, r) for i, r in enumerate(rows) if r.get("tick") == 5970]
    fields = ROW.unpack_from(raw, HEADER.size + i * ROW.size)
    ingress = INGRESS.unpack_from(raw, OFFSET + i * INGRESS.size)
    desc = fields[-1]
    count = list(map(int, logs["budget"]["display_1_30_60"].split(",")))
    return dict(edition=edition, run=run, files={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()},
                samples=len(rows), unresolved=sum("unresolved" in r for r in rows),
                displayed=count, fps=[round(n/d,4) for n,d in zip(count,(29,30))],
                failed_transfers=int(logs["budget"]["failed_transfers"]),
                menu_prepared="stage=MENU_PREPARED" in files["progress"].read_text(),
                final_status={k:int(logs["game-last"][k]) for k in ("native_result","native_receiver_error",
                              "native_sink_error","native_video_error","trace_aborts")},
                sample={**row,"last_descriptor_hex":desc.hex(),"input_bytes":ingress[5]&0xffffff,
                        "input_blocks":ingress[7],"show_ms":row["show_tick"]*MS,
                        "final_ack_ms":row["final_ACK_tick"]*MS})


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder",type=Path)
    p.add_argument("report",type=Path)
    a=p.parse_args()
    reports=[measure(a.folder,e,r) for e in (1034,1035) for r in (1,2)]
    a.report.write_text(json.dumps(reports,indent=2)+"\n",encoding="utf8")

