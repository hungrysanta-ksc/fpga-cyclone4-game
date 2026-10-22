# SPDX-License-Identifier: MIT
"""Run retained independent receipt/STOP/final ACK cases on replacement control."""
import inspect
import guard_nes_joint287 as old
from nes_close295 import apply
from nes_joint296 import apply as joint296
from nes_delta231 import once

def main():
    original=old.apply
    source=inspect.getsource(apply)
    a=source.index("    p=d/'nes_tile_producer260.sv'");b=source.index("    for name in ('nes_plan_rom267.sv'",a)
    ns=dict(once=once);exec('def control(d):\n'+source[a:b],ns)
    def patch(d):original(d);ns['control'](d);joint296(d)
    old.apply=patch
    before=old.old.old.tb
    old.old.old.tb=lambda s:before(s).replace('.end_valid(ev),.end_ready(er),',".end_valid(ev),.end_partial295(1'b0),.end_ready(er),")
    old.main()

if __name__=='__main__':main()
