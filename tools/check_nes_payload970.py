"""Compare the original ARM's WRAM with four proposed pre-tile packet deadlines."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from unicorn import UC_HOOK_BLOCK
from check_nes_output970 import ordinary_first, packet_path
from check_nes_blank959 import directory, read, sha
from nes_feedback953 import evidence
from nes_verified965 import run
from package_nes_trial966 import ROOT, WORK
from replay_nes_supply905 import joint


def observe(temp, phase, prefix, tag):
    ref = directory(temp, phase, "966release", "cold")
    packets, ledger = packet_path(ref, 911)
    reordered = ordinary_first(packets, 911, True)
    early = Path(f"{prefix}-p{phase}-reserved")
    samples = []
    for line in (early / "starts.txt").read_text().splitlines():
        seq, start, _, _ = map(int, line.split())
        packet = bytes.fromhex(reordered[seq-1][3])
        section = packet[1]
        offset = int.from_bytes(packet[10:12], "little")
        if packet[0] != 2 or (section, offset) not in ((3,0), (4,0), (5,1121), (5,1322)):
            continue
        original, = (r for r in ledger if bytes.fromhex(packets[r["index"]-1][3])[4:] == packet[4:]
                     and (r["op"], r["section"]) == (2, section))
        for label, clock in (("reserved", start), ("original", original["issue"])):
            samples.append((clock,label,section,offset,packet[16:]))
    assert len(samples) == 8
    samples.sort()
    records = []
    original_init = joint.Runtime.__init__

    def init(cpu, *args):
        original_init(cpu,*args)
        layout = cpu.layout["nes_native_video165"]
        def sample(u, pc, size, _):
            while samples and cpu.clock >= samples[0][0]:
                target, label, section, offset, expected = samples.pop(0)
                if section == 5:
                    # The two packets share the 441B join buffer at bg_keys + 6144.
                    addr = cpu.video + 6144 + offset - 1121
                else:
                    addr = cpu.video + layout["cgram" if section == 3 else "oam"] + offset
                got = bytes(u.mem_read(addr,len(expected)))
                records.append(dict(section=section,offset=offset,size=len(expected),schedule=label,
                                    target=target,observed=round(cpu.clock),
                                    different_bytes=sum(a!=b for a,b in zip(got,expected,strict=True))))
            if len(records)==8:
                u.hook_del(handle)
        handle = cpu.u.hook_add(UC_HOOK_BLOCK,sample)

    credit = read(ROOT / "analysis/credit965-wire.json")[str(phase)]
    tail = evidence(directory(temp,1,"965wire5","cold"),910,log_name="mail964.log") if phase==1 else None
    with patch.object(joint.Runtime,"__init__",init):
        run(temp,phase,"cold",credit,tail=tail,work=WORK,edition=966,tag=tag)
    observed = directory(temp,phase,tag,"cold")
    for name in ("events.json","window.csv","producer.jsonl","records.bin"):
        assert sha(observed/name)==sha(ref/name), name
    assert not samples and all(r["different_bytes"]==0 for r in records if r["schedule"]=="original")
    return records


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("prefix",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--tag",default="970payload")
    a=p.parse_args()
    a.out.write_bytes((json.dumps(observe(a.temp,a.phase,a.prefix,a.tag),indent=2)+"\n").encode())
