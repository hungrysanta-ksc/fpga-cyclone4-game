# SPDX-License-Identifier: MIT
"""Exercise pre-FINISH input borrowing in the full Cortex-M4 image."""
import argparse
import json
from pathlib import Path

from check_nes_idle676 import ELFFile, Receiver, member_offset
from nes_raw506 import sha


def verify(src, retire_wait=False, bulk_head=False):
    with (src / "obj-nes-100/sd2snes.elf").open("rb") as stream:
        dwarf = ELFFile(stream).get_dwarf_info()
        layouts = {}
        for unit in dwarf.iter_CUs():
            for entry in unit.iter_DIEs():
                name = entry.attributes.get("DW_AT_name")
                if entry.tag != "DW_TAG_structure_type" or not name or "DW_AT_byte_size" not in entry.attributes:
                    continue
                if name.value in (b"nes_plan200", b"nes_resident211", b"nes_sink_window184"):
                    layouts[name.value.decode()] = {
                        field.attributes["DW_AT_name"].value.decode(): member_offset(field)
                        for field in entry.iter_children() if field.tag == "DW_TAG_member"}
    results = {}
    cases = ("owned", "not_prepared", "not_ending", "no_bulk", "progress", "queue_credit", "STOP_after_READ", "bad_CRC")
    for case in cases + (("ordinary_head",) if bulk_head else ()):
        m = Receiver(src, case if case in ("STOP_after_READ", "bad_CRC") else "normal")
        m.layout.update(layouts)
        resident = 0x20016000
        plan = m.rt + m.layout["nes_native_runtime165"]["plan"]
        m.put(m.rt, "nes_native_runtime165", "resident", resident, 4)
        m.put(resident, "nes_resident211", "prepared", int(case != "not_prepared"), 1)
        m.put(plan, "nes_plan200", "ending", int(case != "not_ending"), 1)
        m.put(plan, "nes_plan200", "bulk_pending", int(case != "no_bulk"), 1)
        if bulk_head:
            w = m.rt + m.layout["nes_native_runtime165"]["transport"]
            m.put(w, "nes_sink_window184", "last", 2 if case == "ordinary_head" else 7, 1)
        reason = 0 if case == "queue_credit" else 1
        ok = bool(m.call("wait634", [m.rt, m.check | 1, reason, int(case == "progress")]))
        rejected = case in ("STOP_after_READ", "bad_CRC")
        assert ok != rejected, (case, ok)
        if case == "owned" or (case == "no_bulk" and retire_wait) or (case == "queue_credit" and not retire_wait):
            assert m.ops == [0xd0, 0xd1, 0xd2, 0xd0] and m.index == 1
        elif rejected:
            assert 0xd1 in m.ops and 0xd2 not in m.ops and m.index == 0
        else:
            assert not m.ops and m.index == 0
        assert 0xd3 not in m.ops and 0xea not in m.ops
        results[case] = dict(ok=ok, ops=m.ops, pops=m.index)
    return dict(firmware=sha(src / "obj-nes-100/firmware.stm"), cases=results)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("src", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--retire-wait",action="store_true")
    p.add_argument("--bulk-head",action="store_true")
    a=p.parse_args()
    a.out.write_text(json.dumps(verify(a.src,a.retire_wait,a.bulk_head), indent=2) + "\n", newline="\n")
