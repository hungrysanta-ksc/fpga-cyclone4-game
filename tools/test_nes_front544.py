# SPDX-License-Identifier: MIT
"""Trace the actual frozen-map offer on the linked ARM/65816 shared timeline."""
import argparse,hashlib,json
from pathlib import Path
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R1
import test_nes_raw506_joint as joint
from trace_nes_output531 import OutputRuntime,instrument
from trace_nes_map527 import CheckedLink,run_schedule
from test_nes_tile532 import tile_observer

class Runtime(OutputRuntime):
    def __init__(self,a,link):
        super().__init__(a,link)
        self.frozen544=None
        def snapshot():
            return hashlib.sha256(bytes(self.u.mem_read(self.video+self.layout['nes_native_video165']['map'],4096))).hexdigest()
        def freeze(u,pc,size,unused):
            if not u.reg_read(UC_ARM_REG_R1):return
            self.frozen544=(self.generation,snapshot())
            self.events.append(dict(generation=self.generation,event='frozen_offer544',clock=self.clock,map_SHA256=self.frozen544[1]))
        def prepared(u,pc,size,unused):
            assert self.frozen544==(self.generation,snapshot()),'map changed after frozen offer'
        for symbol,hook in [('offer527',freeze),('nes_resident211_prepare',prepared)]:
            pc=self.syms[symbol];self.u.hook_add(UC_HOOK_CODE,hook,begin=pc,end=pc)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--start-clock',type=int,required=True)
    p.add_argument('--trace-credit',action='store_true');p.add_argument('--trace-rom',action='store_true')
    a=p.parse_args();a.map526=True;joint.Runtime=Runtime
    labels=json.loads((a.client/'labels.json').read_text())
    run_schedule(a,lambda s,args:tile_observer(instrument(s,args),labels,'128'),CheckedLink,frames=53)
