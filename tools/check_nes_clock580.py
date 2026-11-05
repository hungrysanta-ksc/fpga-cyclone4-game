# SPDX-License-Identifier: MIT
"""Execute the real SPI hook body with deterministic boundary doubles.

Only RPC/register/memory boundaries are mocked. Compare old and fixed hook
effects on final and nonfinal D2, including capture phase and RPC overshoot.
This is a logger regression, not a complete M4/65816 simulation.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS

SOURCE=Path(__file__).with_name('test_nes_raw506_joint.py')
MASTER=21477272
PERIOD=341*262*4


def compile_hook(source):
    tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Runtime')
    hook=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='hook')
    env=dict(math=math,MASTER=MASTER,PERIOD=PERIOD,ARM_HZ=84000000)
    for name in ['SP','R0','R1','R2','R3','PC','LR']:env['UC_ARM_REG_'+name]=name
    exec(compile(ast.Module(body=[hook],type_ignores=[]),str(SOURCE),'exec'),env)
    return env['hook']


def run(hook,final,phase,overshoot):
    regs=dict(SP=0x20001000,R1=0x100,R2=0x200,R3=8,LR=0x300)
    tx=b'\xd2\x00\x00\x07'+bytes(4);writes=[];rpc=[]
    def sync(clock):
        rpc.append(clock)
        return math.ceil(clock)+overshoot
    u=NS(reg_read=lambda r:regs[r],reg_write=lambda r,v:regs.__setitem__(r,v),
         mem_read=lambda a,n:tx,mem_write=lambda a,b:writes.append((a,bytes(b))))
    m=NS(live=True,end=-1,irq=False,clock=3447000.,next_irq=1e30,
         instructions=0,a=NS(cpi=2,spi_us=0,rom_phase=phase),min_sp=1e30,
         workspace_end=0x20000000,ticks_cb=-2,service_cb=-3,syms={},spi=0x400,
         link=NS(rpc=sync),status=lambda:bytes(8),driver_extra={0xd2:37.5},
         start_token=7,index=0,packets=[b'a']*(1 if final else 2),
         next_capture_ready=42,wire_B={},events=[],generation=905)
    hook(m,u,0x400,2,None)
    return dict(clock=m.clock,next_capture_ready=m.next_capture_ready,index=m.index,
                instructions=m.instructions,wire_B=m.wire_B,events=m.events,
                registers=regs,writes=[(a,b.hex()) for a,b in writes],rpc=rpc)


def main():
    fixed=SOURCE.read_text(encoding='utf8')
    a='capture_start=(math.floor((self.clock-self.a.rom_phase)/PERIOD)+1)*PERIOD+self.a.rom_phase\n                self.next_capture_ready=capture_start+240*341*4'
    b=a.replace('capture_start','start')
    assert fixed.count(a)==1
    original=fixed.replace(a,b)
    old,new=compile_hook(original),compile_hook(fixed);cases=[]
    for final in [False,True]:
        for phase in [0,178684]:
            for overshoot in [0,512]:
                before=run(old,final,phase,overshoot);after=run(new,final,phase,overshoot)
                old_start=before['events'][0]['start'];new_start=after['events'][0]['start']
                assert new_start<=after['events'][0]['clock']
                if final:
                    assert old_start>before['clock']
                    assert before['next_capture_ready']==old_start+240*341*4
                else:assert old_start==new_start and before['next_capture_ready']==42
                before['events'][0]['start']=new_start
                assert before==after
                cases.append(dict(final_D2=final,phase=phase,RPC_overshoot=overshoot,
                                  original_start=old_start,fixed_start=new_start,
                                  end=after['clock'],capture_ready=after['next_capture_ready']))
    print(json.dumps(dict(passed=True,cases=cases,
        source_sha256=hashlib.sha256(fixed.encode()).hexdigest(),
        scope='Real hook body with mocked boundaries; all state/RPC/write effects equal except final D2 logged start.'),indent=2))


if __name__=='__main__':main()
