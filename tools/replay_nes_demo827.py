"""Read the cost counter arguments from the linked ARM, without changing the target."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import WORK, joint, main
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1


def replay(variant, group, phase, temp, budget):
    original = joint.Runtime.__init__

    def attach(cpu, *args):
        original(cpu, *args)
        costs = []
        def phase_return(u, address, size, data):
            if u.reg_read(UC_ARM_REG_R0) != 2:
                return
            now = int(cpu.clock * joint.ARM_HZ / joint.MASTER)
            cycles = (now - u.reg_read(UC_ARM_REG_R1)) & 0xffffffff
            costs.append(dict(end=cpu.clock, start=cpu.clock-cycles*joint.MASTER/joint.ARM_HZ))
            (cpu.a.out/"output-phase.json").write_text(json.dumps(costs))
        addr = cpu.syms["nes_cost471_phase"] & ~1
        cpu.u.hook_add(UC_HOOK_CODE, phase_return, begin=addr, end=addr)

    root = WORK.parent
    src = root / "nes-output823" / ("link-826" if variant=="baseline" else "link-827"+variant) / "src"
    folders={"earlyB":"extra01","late":"data02","demoB":"demo-extra01","demoD":"demo-extra01"}
    clips = root/"nes-trial825/data" if group=="change" else root/"nes-tile821"/folders[group]
    lookup = temp/"nes-demo825-cache/hits.json" if group=="change" else MirrorLink.lookup_file
    with patch.object(joint.Runtime,"__init__",attach), patch.object(
            sys,"argv",["replay","","","","","","827-mark-"+variant,str(budget)]), patch.object(MirrorLink,"lookup_file",lookup):
        main(clips,group,"jointmirror",phase,temp,arm=src,link_class=MirrorLink)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("variant")
    p.add_argument("group",choices=("earlyB","late","demoB","demoD","change"))
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    args=p.parse_args()
    replay(**vars(args))
