"""Recheck the linked ARM recovery and fault the same 23-row client before publication."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from check_nes_menu533 import check
from check_nes_output970 import packet_path, replay
from check_nes_sram897 import check_game_path
from nes_order938 import empty_next_offer
from nes_tail1013 import ROOT, VARIANTS, WORK


def guards(temp,mode):
    root=WORK/mode
    src=root/"link/src"
    cases,ram,entry=check_game_path(src,order=empty_next_offer)
    (root/"guards.json").write_text(json.dumps(dict(sram=ram,entry=entry,cases=cases,menu=check(src,"1012"))))
    if not (root/"recovery/result.json").exists():
        subprocess.run([sys.executable,ROOT/"tools/check_nes_transfer512_recovery.py","--arm",src,"--trial","1012",
                        "--fault","none","--out",root/"recovery"],check=True)
    trace=temp/f"nes-tile821-late-jointmirror-p1-1013c-{mode}"
    heads=[bytes.fromhex(json.loads(line)[2]) for line in (trace/"packets.jsonl").read_text().splitlines()]
    frame=[h for h in heads if int.from_bytes(h[8:10],"little")==908]
    commands,_=packet_path(trace,908,expected_shape=(len(frame),sum(h[0]==7 for h in frame)))
    result={}
    for fault in ("bad_seal","stop_decode"):
        result[fault]=replay(temp,trace,temp/f"nes-tail1013-guard-{mode}-{fault}","fixed",commands,908,fault)
    (root/"faults.json").write_text(json.dumps(result))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("mode",choices=VARIANTS)
    a=p.parse_args()
    guards(a.temp,a.mode)
