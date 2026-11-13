"""Run the linked timer, normal/fault exit, menu and base checks for a trial."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import UC_HOOK_CODE, sha
from check_nes_longrun693 import Probe
from package_nes_trial704 import checked


def timed(src):
    rows = {}
    for name, start, elapsed, fault, expected in (
        ("early", 0, 5999, False, 0), ("deadline", 0, 6000, False, 1),
        ("wrapped", 0xfffffff0, 6000, False, 1), ("fault_at_deadline", 0, 6000, True, 2),
    ):
        q = Probe(src)
        q.board = True
        q.now = (start + elapsed) & 0xffffffff
        q.fault = fault
        q.u.mem_write(q.data["ticks"], q.now.to_bytes(4, "little"))
        q.put(q.rt, "nes_native_runtime165", "started", start, 4)
        q.put(q.rt, "nes_native_runtime165", "service", q.syms["native_service165"] | 1, 4)
        q.put(q.resident, "nes_resident211", "open", 1, 1)
        ok = q.call("nes_runtime165_step", [q.rt])
        assert bool(ok) == (expected == 0)
        assert q.get(q.rt, "nes_native_runtime165", "result") == expected
        if expected:
            assert not q.ops and not q.get(q.resident, "nes_resident211", "open")
        rows[name] = expected

    for reason, frames, error in ((1, 3, 0), (1, 0, 4), (8, 0, 0), (2, 3, 4)):
        q = Probe(src)
        def terminal(cpu, address, size, context):
            if address == q.syms["nes_runtime165_step"]:
                q.put(q.rt, "nes_native_runtime165", "result", reason, 1)
                q.put(q.rt, "nes_native_runtime165", "frames", frames, 4)
                q.ret(cpu, 0)
            else:
                q.ret(cpu, 1)
        for fn in ("nes_runtime165_step", "nes_runtime165_begin", "nes_cost471_begin", "nes_cost471_end"):
            q.u.hook_add(UC_HOOK_CODE, terminal, begin=q.syms[fn], end=q.syms[fn])
        entry, = (fn for fn in q.syms if fn.startswith("native_frames222"))
        q.call(entry, [1, 1])
        assert q.get(q.data["nes_run136"], "nes_run136_report", "first_error") == error
        assert not q.get(q.rt, "nes_native_runtime165", "resident", 4)
        rows[f"terminal_{reason}_{frames}"] = error
    return dict(firmware=sha(src / "obj-nes-100/firmware.stm"), cases=rows)


def run(number, src, out):
    out.mkdir(parents=True, exist_ok=False)
    def execute(script, args, tag):
        checked(script, args, out / (tag + ".log"))
    execute("check_nes_menu533.py", ["--arm", src, "--trial", number, "--out", out / "menu.json"], "menu")
    for fault in ("none", "program", "done", "busy", "token"):
        tag = "base-" + fault
        execute("check_nes_transfer512_recovery.py", ["--arm", src, "--trial", number, "--fault", fault, "--out", out / tag], tag)
    if number in ("763", "765"):
        execute("check_nes_windows518.py", ["--arm", src, "--layout", "trimmed", "--out", out / "mode.json"], "mode")
        if number == "765":
            (out / "timer.json").write_text(json.dumps(timed(src), indent=2) + "\n")
    else:
        execute("check_nes_longrun693.py", ["--arm", src, "--out", out / "mode.json"], "mode")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial", choices=["763", "764", "765", "766"])
    parser.add_argument("arm", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    run(args.trial, args.arm.resolve(), args.out.resolve())
