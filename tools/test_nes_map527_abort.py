# SPDX-License-Identifier: MIT
"""Inject a guard failure or invalid OBJ after a real speculative map E1 on the linked joint path."""
import argparse
import json
from pathlib import Path

import test_nes_raw506_joint as joint
from check_nes_game478 import UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R3
from test_nes_idle524_schedule import observe
from test_nes_map526_schedule import observer
from test_nes_trim514_schedule import run_schedule
from trace_nes_map527 import MapRuntime
from trace_nes_obj518 import ObjLink


class FaultRuntime(MapRuntime):
    injected=False

    def hook(self,u,pc,size,user):
        if self.injected and self.a.fault=='guard' and pc==self.service_cb:
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        match=False
        if self.live and self.generation==906 and pc==self.spi and not self.injected:
            tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R3)))
            match=tx[0]==0xe1 and tx[1] in (2,4) and tx[2]==2
        super().hook(u,pc,size,user)
        if match:
            assert not any(e['generation']==906 and e['event']=='end_enter' for e in self.events)
            self.injected=True
            if self.a.fault=='invalid_OBJ':
                layout=self.layout['nes_native165']
                item=self.state+layout['objects']
                u.mem_write(item+7,b'\x80')  # reserved bit, rejected on the subsequent OBJ walk

    def call(self,name,args):
        ok=super().call(name,args)
        if self.live and name=='nes_runtime165_step' and not ok and self.injected:
            r=self.resident;s=self.rt+self.layout['nes_native_runtime165']['sink']
            def byte(field):return self.get(r,'nes_resident211',field)
            assert byte('fault') and not byte('open') and not byte('prepared')
            assert byte('target')!=byte('active') and byte('displayed')
            assert self.get(s,'nes_native_sink165','last_generation',2)==905
            assert bytes(self.u.mem_read(r+self.layout['nes_resident211']['map_stale'],16))==b'\xff'*16
            (self.a.out/'guard-proof.json').write_text(json.dumps(dict(injected=self.a.fault,last_display=905,
                aborted=906,runtime_result=self.get(self.rt,'nes_native_runtime165','result'),
                invalidated_both_map_banks=True))+'\n')
        return ok


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--start-clock',type=int,required=True)
    p.add_argument('--fault',choices=('guard','invalid_OBJ'),required=True)
    a=p.parse_args();joint.Runtime=FaultRuntime
    try:run_schedule(a,lambda s,args:observe(s,args,observer),ObjLink,frames=2)
    except AssertionError as error:
        if not error.args or not isinstance(error.args[0],tuple) or error.args[0][:2]!=('runtime fault',906):raise
        proof=json.loads((a.out/'guard-proof.json').read_text())
        packets=[bytes.fromhex(json.loads(l)[2]) for l in (a.out/'packets.jsonl').read_text().splitlines()]
        assert [int.from_bytes(b[8:10],'little') for b in packets if b[0]==3]==[905]
        assert any(b[0] in (2,4) and b[1]==2 and int.from_bytes(b[8:10],'little')==906 for b in packets)
        assert not any(e['event']=='SPI' and e['opcode']=='0xea' and e['generation']==906
                       for e in json.loads((a.out/'events.json').read_text()))
        print(proof)
    else:raise AssertionError('injected fault reached normal completion')
