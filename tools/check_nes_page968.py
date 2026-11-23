"""Observe the successful page store in the unchanged MMC966 ARM link."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R4, UC_ARM_REG_R6
from check_nes_blank959 import directory, read, sha
from nes_feedback953 import evidence
from nes_verified965 import run
from package_nes_trial966 import ROOT, WORK
from replay_nes_supply905 import joint
from test_nes_service509_schedule import Calendar


def replay(temp, phase, tag):
    writes = []
    original_init = joint.Runtime.__init__

    def init(cpu, *args):
        original_init(cpu, *args)
        site = cpu.syms["page964"] + 0x20
        if bytes(cpu.u.mem_read(site, 4)) != bytes.fromhex("a6f89616"):
            raise ValueError("wrong MMC966 page store")

        def store(u, address, size, user):
            if u.reg_read(UC_ARM_REG_R4) != 255:
                return
            receiver = u.reg_read(UC_ARM_REG_R6) - 8192
            offset = cpu.layout["nes_native165"]["generation"]
            generation = int.from_bytes(u.mem_read(receiver + offset, 2), "little")
            writes.append((generation, u.reg_read(UC_ARM_REG_R1)-1, round(cpu.clock)))

        cpu.u.hook_add(UC_HOOK_CODE, store, begin=site, end=site)

    record = read(ROOT/"analysis/credit965-wire.json")[str(phase)]
    tail = evidence(directory(temp, 1, "965wire5", "cold"), 910, log_name="mail964.log") if phase == 1 else None
    with patch.object(joint.Runtime, "__init__", init):
        run(temp, phase, "cold", record, tail=tail, work=WORK, edition=966, tag=tag)
    folder = directory(temp, phase, tag, "cold")
    reference = directory(temp, phase, "966release", "cold")
    for filename in ("events.json", "window.csv", "producer.jsonl", "hint963.json", "records.bin"):
        if sha(folder/filename) != sha(reference/filename):
            raise ValueError(f"observation changed replay: {filename}")
    events = read(folder/"events.json")
    hints = read(folder/"hint963.json")
    result = []
    for gen, base, accepted, _ in hints["hints"]:
        confirmed, = (at for g, page, at in writes if (g, page) == (gen, base))
        eb, = (e for e in events if e.get("opcode") == "0xeb" and e["generation"] == gen)
        plan = next(e for e in events if e.get("opcode") == "0xe9" and e["generation"] == gen)
        assert confirmed <= eb["start"] < accepted < plan["clock"] and round(eb["clock"]) == accepted
        grants = [entry for entry in hints["fills"] if entry[0] == gen]
        first = [entry for entry in grants if entry[1]//16 == base]
        if first and [entry[1]%16 for entry in first] != list(range(8)):
            raise ValueError("first page tile rows incomplete")
        result.append(dict(generation=gen, tag=base, confirmed=confirmed, EB_start=round(eb["start"]),
                           EB_complete=accepted, E9_start=round(plan["start"]), E9_complete=round(plan["clock"]),
                           grants=len(grants), first_tile_grants=[entry[2] for entry in first],
                           confirm_to_EB_start_ms=round((eb["start"]-confirmed)*1000/joint.MASTER, 5)))
    return result


def calendar_bounds(temp, phase, records):
    calendar = Calendar(temp/"nes-service509-rom03")
    events = read(directory(temp, phase, "966release", "cold")/"events.json")
    for r in records:
        previous_ea, = (e for e in events if e.get("opcode") == "0xea"
                         and e["generation"] == r["generation"]-1)
        at = r["confirmed"]
        slots = []
        while at < r["EB_complete"]:
            grant, reply = calendar.select(at)
            if grant >= r["EB_complete"]:
                break
            slots.append(grant)
            at = reply+1
        r.update(previous_EA_complete=round(previous_ea["clock"]), prior_calendar_slots=len(slots),
                 last_prior_slot=slots[-1] if slots else None,
                 prior_slots_after_EA=sum(g >= previous_ea["clock"] for g in slots))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--tag", default="968observe")
    args = p.parse_args()
    data = {phase: replay(args.temp, phase, args.tag) for phase in (1, 2)}
    for phase, records in data.items():
        calendar_bounds(args.temp, phase, records)
    args.output.write_bytes((json.dumps(data, indent=2)+"\n").encode())
