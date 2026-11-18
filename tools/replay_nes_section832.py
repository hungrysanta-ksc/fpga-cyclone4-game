"""Trace section 5 SPI against OBJ tile reads on the linked no-input demo."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import joint, main
from prepare_nes_section832 import BASE, OUT, PROBES
from check_nes_game478 import sha
from replay_nes_seal831 import after_display2572
from unicorn import UC_HOOK_CODE


class TraceLink(MirrorLink):
    def decode557(self, q, arrived, now):
        start = super().decode557(q, arrived, now)
        if start <= now:
            self.slot832 = int.from_bytes(q[2:4], "little") * 32
        return start

    def next_rom(self, t):
        kind, address = self.pending[0]
        end = super().next_rom(t)
        if kind == 1 and self.generation == 909:
            self.reads832.append((self.slot832, address, t, end))
        return end

    def __init__(self, args):
        super().__init__(args)
        self.reads832 = []

    def exchange(self, seq, t, op, args):
        if op == "FINISH":
            (self.a.out/"obj-reads832.json").write_text(json.dumps(self.reads832))
        return super().exchange(seq, t, op, args)


def run(mode, phase, temp, budget, fixed=False, tail=False, *, arm=None, overlay_root=OUT,
        tag=None, client=None, adapt=None, on_attach=None):
    assert not tail or fixed
    arm = arm or (BASE if mode == "base" else PROBES/"nes-output823"/("link-832"+mode))
    original = joint.Runtime.__init__
    def attach(cpu, *args):
        original(cpu, *args)
        if on_attach:
            on_attach(cpu)
        def mark(u, address, size, data):
            if cpu.link.generation == 909:
                (cpu.a.out/"section-ready832.txt").write_text(str(cpu.clock))
        pos = cpu.syms["nes_sink212_seal"] & ~1
        if fixed:
            overlay=overlay_root/("overlay-"+mode)
            entry=json.loads((overlay/"entry.json").read_bytes())
            assert entry["parent"]==sha(BASE/"src/obj-nes-100/firmware.stm")
            assert entry["sink"]==sha(overlay/"sink.bin")
            cpu.u.mem_write(0x08060000,(overlay/"sink.bin").read_bytes())
            pos=entry["entry"]
            cpu.patches832=entry
        cpu.u.hook_add(UC_HOOK_CODE, mark, begin=pos, end=pos)
    original_call=joint.Runtime.call
    def call(cpu,name,args):
        if fixed and name=="nes_runtime165_step" and cpu.generation==909 and hasattr(cpu,"patches832"):
            entry=cpu.patches832
            for pc,old,new in entry["patches"]:
                assert bytes(cpu.u.mem_read(pc,4)).hex()==old
                cpu.u.mem_write(pc,bytes.fromhex(new))
                cpu.u.ctl_remove_cache(pc,pc+4)
            (cpu.a.out/"fixed832.json").write_text(json.dumps(dict(clock=cpu.clock,**entry)))
            del cpu.patches832
        return original_call(cpu,name,args)
    with patch.object(joint.Runtime, "__init__", attach), patch.object(joint.Runtime,"call",call), patch.object(
            sys, "argv", ["replay","","","","","",tag or ("832"+mode+("tail" if tail else "")+("fixed" if fixed else "")),str(budget)]):
        main(PROBES/"nes-tile821/demo-extra01", "demoB", "jointmirror", phase,
             temp, arm=(BASE if fixed else arm)/"src", link_class=TraceLink,
             client=client,client_hash=sha(client/"sink165.sfc") if client else None,
             adapt_template=adapt or ((lambda s:after_display2572(s,PROBES/"nes-seal831/client-tail")) if tail else None))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode")
    parser.add_argument("phase", type=int, choices=(1, 2))
    parser.add_argument("temp", type=Path)
    parser.add_argument("budget", type=Path)
    parser.add_argument("--fixed",action="store_true")
    parser.add_argument("--tail",action="store_true")
    run(**vars(parser.parse_args()))
