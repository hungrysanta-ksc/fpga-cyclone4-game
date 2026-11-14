"""Replay the deployed boot-before-RUN boundary at multiple MCU uptimes."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_longrun693 import Probe, UC_HOOK_CODE
from check_nes_trial763 import timed


def boot(src, ticks, fault=False):
    q = Probe(src)
    q.board, q.stage, q.now, q.fault = True, 3, ticks, fault
    # Probe normally starts after RUN begin. Restore the actual pre-boot BSS state.
    q.u.mem_write(q.rt, bytes(q.layout["nes_native_runtime165"]["size"]))
    q.u.mem_write(q.data["nes_run136"], bytes(q.layout["nes_run136_report"]["size"]))
    q.u.mem_write(q.data["native_first165"], b"\x01")
    q.u.mem_write(q.data["ticks"], struct.pack("<I", ticks))
    q.u.mem_write(q.data["native_observed165"], struct.pack("<I", ticks))
    at = q.syms["boot214_signals"]
    q.u.hook_add(UC_HOOK_CODE, lambda cpu, pc, size, user: q.ret(cpu,6), begin=at, end=at)
    ok = q.call("native_boot172", [0])
    reason,polls,elapsed,first,last,_ = struct.unpack("<6I", q.u.mem_read(q.data["nes_boot214"],24))
    return dict(ready=bool(ok), reason=reason, polls=polls, ticks=elapsed, first=first,last=last, spi=q.calls)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("old","new","out"):
        p.add_argument(k,type=Path)
    a=p.parse_args()
    rows={}
    for tick in (5999,6000,25000,0xfffffff0):
        old,new=boot(a.old,tick),boot(a.new,tick)
        assert old["ready"]==(tick<6000) and new["ready"] and new["reason"]==1
        if tick>=6000:
            assert old["reason"]==2 and old["polls"]==1 and old["ticks"]==old["first"]==old["last"]==0 and not old["spi"]
        rows[tick]=dict(old=old,new=new)
    assert not boot(a.new,25000,True)["ready"]
    a.out.write_text(json.dumps(dict(boot=rows, hardware_fault_blocked=True,run=timed(a.new)),indent=2)+"\n")
