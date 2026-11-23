"""Bracket the last ARM basic block with unfinished packet bytes, on the original MMC966 link."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from unicorn import UC_HOOK_BLOCK
from check_nes_blank959 import directory, read, sha
from check_nes_output970 import packet_path
from nes_feedback953 import evidence
from nes_verified965 import run
from package_nes_trial966 import ROOT, WORK
from replay_nes_supply905 import joint


def observe(temp, phase, tag):
    ref = directory(temp, phase, "966release", "cold")
    proof = read(ROOT / "analysis/output970-results.json")["phases"][str(phase)]["911"]
    packets, path = packet_path(ref, 911)
    checks = []
    for event in path:
        packet = bytes.fromhex(packets[event["index"]-1][3])
        section, offset = packet[1], int.from_bytes(packet[10:12],"little")
        if packet[0] == 2 and (section, offset) in ((3,0),(4,0),(5,1121),(5,1322)):
            deadline, = (r["target"] for r in proof["arm_payload"]
                         if (r["schedule"],r["section"],r["offset"]) == ("reserved",section,offset))
            checks.append(dict(section=section, offset=offset, data=packet[16:], send=event["issue"],
                               deadline=deadline, last_mismatch=None, first_stable=None))
    assert len(checks) == 4
    start = path[0]["issue"]
    original = joint.Runtime.__init__

    def init(cpu,*args):
        original(cpu,*args)
        layout = cpu.layout["nes_native_video165"]
        def sample(u, pc, size, _):
            at = round(cpu.clock)
            if at < start:
                return
            for row in checks:
                if at > row["send"]:
                    continue
                section = row["section"]
                addr = 6144 + row["offset"]-1121 if section==5 else layout["cgram" if section==3 else "oam"]
                if bytes(u.mem_read(cpu.video+addr,len(row["data"]))) != row["data"]:
                    row["last_mismatch"],row["first_stable"] = at,None
                elif row["first_stable"] is None:
                    row["first_stable"] = at
            if at > checks[-1]["send"]:
                u.hook_del(handle)
        handle = cpu.u.hook_add(UC_HOOK_BLOCK,sample)

    tail = evidence(directory(temp,1,"965wire5","cold"),910,log_name="mail964.log") if phase==1 else None
    with patch.object(joint.Runtime,"__init__",init):
        run(temp,phase,"cold",read(ROOT/"analysis/credit965-wire.json")[str(phase)],tail=tail,work=WORK,edition=966,tag=tag)
    folder = directory(temp,phase,tag,"cold")
    for name in ("events.json","window.csv","producer.jsonl","records.bin"):
        assert sha(ref/name)==sha(folder/name)
    for row in checks:
        row["bytes"] = len(row.pop("data"))
        assert row["last_mismatch"] < row["first_stable"] <= row["send"]
    return checks


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("out",type=Path)
    p.add_argument("--tag",default="971ready")
    a=p.parse_args()
    a.out.write_text(json.dumps(observe(a.temp,a.phase,a.tag),indent=2)+"\n")
