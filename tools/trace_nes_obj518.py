# SPDX-License-Identifier: MIT
"""Join accepted OBJ plans and ROM service to the real 65816 consumer clock."""
import argparse
import json
import struct
from collections import deque
from pathlib import Path

from nes_transfer512_rpc import PipeLink
from test_nes_trim514_schedule import run_schedule
from test_nes_window516 import instrument


class ObjLink(PipeLink):
    def __init__(self, args):
        self.owners = deque()
        self.phases = {}
        super().__init__(args)

    def accept(self, tx, t):
        g = self.generation
        phase = self.phases.setdefault(g, {})
        if tx[0] == 0xe9:
            plans = self.plansets[g]
            stop = self.plan_at + tx[3]
            assert stop <= len(plans) + 1
            for plan in plans[self.plan_at:stop]:
                gen, slot, _, kind, mask = struct.unpack_from("<HHHBB", plan)
                assert gen == g
                if kind != 2:
                    self.owners.extend([(g, kind)] * (2 * mask.bit_count()))
                if kind == 1:
                    phase.setdefault("obj_plans", []).append(dict(slot=slot, accepted_clock=t))
            if stop == len(plans) + 1:
                phase["end_accepted"] = t
        end = super().accept(tx, t)
        if tx[0] == 0xea:
            assert not self.owners and "end_accepted" in phase
            phase["ea"] = end
            (self.a.out / "obj-phases.json").write_text(json.dumps(self.phases, indent=2) + "\n")
        return end

    def next_rom(self, request):
        g, kind = self.owners.popleft()
        response = super().next_rom(request)
        if kind == 1:
            phase = self.phases[g]
            phase.setdefault("first_obj_rom_request", request)
            phase["last_obj_rom_response"] = response
            phase["obj_rom_reads"] = phase.get("obj_rom_reads", 0) + 1
        return response


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("arm", "data", "fixture", "plans", "client", "mesen", "out", "calendar", "driver503", "capture"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--start-clock", type=int, default=3000000)
    p.add_argument("--frames", type=int, choices=range(1,72), default=12, metavar="1..71")
    args = p.parse_args()
    run_schedule(args, instrument, ObjLink, frames=args.frames)
