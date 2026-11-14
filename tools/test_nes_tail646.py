"""Observe writes in the linked M4 while running the production 65816 and the 636 joint schedule."""
import runpy
from unittest.mock import patch
from check_nes_game478 import UC_HOOK_CODE
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_MEM_WRITE


def watch(original, complete="nes_plan200_end"):
    def init(cpu, args, link):
        original(cpu, args, link)
        layout = cpu.layout["nes_native_video165"]
        regions = {"oam": (layout["oam"], 544), "cgram": (layout["cgram"], 512),
                   "scroll": (layout["hdma"], 1121), "scroll_length": (layout["hdma_size"], 2),
                   "raw": (layout["bg_keys"], 2048), "tables": (layout["bg_keys"]+2048, 243),
                   "sizes": (layout["bg_keys"]+2292, 6), "valid": (layout["valid"], 1)}
        handles = []
        stamps = {}

        def start(u, pc, size, user):
            if cpu.generation not in (954, 955):
                return
            assert not handles
            stamps.clear()
            def written(u, access, address, width, value, name):
                stamps[name] = cpu.clock
            for name, (offset, length) in regions.items():
                addr = cpu.video + offset
                handles.append(u.hook_add(UC_HOOK_MEM_WRITE, written, name, begin=addr, end=addr+length-1))

        def done(u, pc, size, user):
            if not handles:
                return
            for handle in handles:
                u.hook_del(handle)
            handles.clear()
            assert set(stamps) == set(regions) and bytes(u.mem_read(cpu.video+layout["valid"],1))==b"\1"
            cpu.events.append(dict(generation=cpu.generation,event="last_writes646",clock=cpu.clock,writes=stamps.copy()))
        for name, fn in (("nes_native_video211_plan", start), (complete, done)):
            pc = cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE, fn, begin=pc, end=pc)
    return init


if __name__ == "__main__":
    with patch.object(Runtime,"__init__",watch(Runtime.__init__)):
        runpy.run_module("test_nes_export636",run_name="__main__")
