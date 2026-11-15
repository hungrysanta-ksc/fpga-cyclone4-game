# SPDX-License-Identifier: MIT
"""Compare actual 951/953/959 block decodes and exercise the checked output handoff."""
import argparse
from hashlib import sha256
from pathlib import Path
import json

from check_nes_commit790 import verify
from check_nes_decode787 import evaluate, sealed_budgets
from check_nes_game478 import Machine
from prepare_nes_tail791 import MODES


def profile(src, blocks):
    cpu = Machine(src, bytes(128))
    size = cpu.layout["nes_native165"]["size"]
    result = []
    # The final COMMIT requires the verified D3 handoff, tested by verify().
    assert bytes.fromhex(blocks[-1]["wire"])[:2] == bytes.fromhex("e003")
    for token, block in enumerate(blocks[:-1]):
        wire = bytes.fromhex(block["wire"])
        cpu.u.mem_write(0x20006000, wire)
        before = cpu.instructions
        assert cpu.call("nes_native165_packet", [cpu.state, token, 0x20006000, len(wire)])
        result.append(dict(bytes=len(wire), instructions=cpu.instructions-before,
                           receiver=sha256(cpu.u.mem_read(cpu.state, size)).hexdigest()))
    assert cpu.state_value() == 2
    return result


def packed_guards(src):
    import struct
    cpu = Machine(src, bytes(128))
    fields = cpu.layout["nes_native165"]
    results = {}
    # Use two map row groups. Values 0..15 are valid row selectors.
    for name, kind, n, at, next_kind, generation, lane, accepted in (
        ("one_row", 1, 1, 223, 1, 951, 15, True),
        ("row_tail", 1, 3, 221, 1, 951, 0x0f0001, True),
        ("row_bad_middle", 1, 3, 221, 1, 951, 0x011002, False),
        ("row_pad", 1, 3, 221, 1, 951, 0x01000102, False),
        ("row_short_count", 1, 2, 221, 1, 951, 0x0102, False),
        ("palette_tail", 5, 3, 61, 5, 951, 0x013f02, True),
        ("palette_bad_middle", 5, 3, 61, 5, 951, 0x014002, False),
        ("palette_before_rows", 5, 8, 0, 1, 951, 0, False),
        ("other_generation", 1, 1, 223, 1, 952, 0, False),
    ):
        cpu.call("nes_native165_reset", [cpu.state])
        def field(key, value, length, idx=0):
            cpu.u.mem_write(cpu.state+fields[key]+length*idx, value.to_bytes(length,"little"))
        field("generation",951,2)
        field("state",1,1)
        field("next_kind",next_kind,1)
        for index,count in ((0,66),(1,224),(5,64)):
            field("counts",count,2,index)
        field("at",at,2,kind)
        packet=struct.pack(">HHQ",0xf800|(kind<<8)|(n-1),generation,lane)
        cpu.u.mem_write(0x20006000,packet)
        ok=bool(cpu.call("nes_native165_packet",[cpu.state,0,0x20006000,len(packet)]))
        assert ok==accepted,(name,ok)
        # Poisoned state includes the count and bytes of any accepted prefix.
        results[name]=dict(accepted=ok,state=sha256(cpu.u.mem_read(cpu.state,fields["size"])).hexdigest())
    return results


def rom_service(src):
    from check_nes_credit752 import Handoff
    from check_nes_idle676 import Receiver
    fields = Handoff(src, "normal").layout
    cases = []
    for case in ("ready", "output_progress", "not_prepared", "not_ending",
                 "empty", "STOP_before", "STOP_after_READ", "bad_CRC", "bad_retire"):
        endpoint = case if case in ("empty", "STOP_before", "STOP_after_READ", "bad_CRC", "bad_retire") else "normal"
        m = Receiver(src, endpoint)
        m.layout["nes_plan200"] = fields["nes_plan200"]
        m.layout["nes_resident211"] = fields["nes_resident211"]
        resident = 0x20008000
        m.put(m.rt, "nes_native_runtime165", "resident", resident, 4)
        m.put(resident, "nes_resident211", "prepared", int(case!="not_prepared"), 1)
        m.put(resident, "nes_resident211", "tile_boundary", 1, 4)
        plan = m.rt+m.layout["nes_native_runtime165"]["plan"]
        m.put(plan, "nes_plan200", "ending", int(case!="not_ending"), 1)
        ok = m.call("wait634", [m.rt, m.check|1, 0, int(case=="output_progress")])
        fail = case in ("STOP_before","STOP_after_READ","bad_CRC","bad_retire")
        assert bool(ok) != fail, (case,ok,m.ops)
        if case=="ready":
            assert m.ops==[0xd0,0xd1,0xd2,0xd0] and m.index==1
        if case in ("not_ending","not_prepared","output_progress","STOP_before"):
            assert not m.ops
        if case=="empty":
            assert m.ops==[0xd0] and m.index==0
        if case in ("STOP_after_READ","bad_CRC"):
            assert 0xd2 not in m.ops
        assert not any(op in (0xd3,0xe1,0xea) for op in m.ops)
        cases.append(dict(case=case,ok=bool(ok),ops=m.ops))
    return cases


def check(base, src, sender, mode):
    guard = verify(src, True, batch_empty_status=mode in ("rom_seal","counts_wait","lane_wait"))
    if mode in ("rom_wait", "rom_seal", "packed_wait", "counts_wait", "lane_wait"):
        guard["ROM_wait"] = rom_service(src)
    cases = evaluate(src)
    assert cases == evaluate(base)
    guard["malformed_and_valid_records"] = cases
    guard["sealed_service"] = sealed_budgets(src)
    guard["packed_cases"] = packed_guards(src)
    assert guard["packed_cases"] == packed_guards(base)
    blocks = json.loads(sender.read_bytes())
    guard["profiles"] = {}
    for gen in ("951", "953", "959"):
        old = profile(base, blocks[gen])
        new = profile(src, blocks[gen])
        assert [r["receiver"] for r in old] == [r["receiver"] for r in new]
        guard["profiles"][gen] = new
    return guard


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "src", "sender", "out"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--mode", choices=MODES, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(check(args.base, args.src, args.sender, args.mode), indent=2)+"\n", newline="\n")
