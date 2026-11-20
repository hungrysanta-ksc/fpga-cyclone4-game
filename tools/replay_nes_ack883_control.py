"""Change only the 907 final-status retry budget in the pinned 882 ARM replay."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from analyze_nes_map830 import load, window
from check_nes_oam882 import capture
from check_nes_strip869 import digest
from replay_nes_strip869 import dense, run
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP


def control(temp, work):
    fw = work/'link-credit/src/obj-nes-100/firmware.stm'
    assert digest(fw) == '55ab84f51452876ce214f8c4db92d767eeb381259c3bf5f090ae133bd2a4cd84'
    runtime = dense.joint.Runtime
    init, call = runtime.__init__, runtime.call
    changed = []

    class Done(Exception):
        pass

    def step(cpu, name, args, *rest, **kw):
        if name=='nes_runtime165_step' and cpu.generation==911:
            raise Done
        return call(cpu,name,args,*rest,**kw)

    def attach(cpu,args,link):
        init(cpu,args,link)
        saved=None
        returns=set()
        def restore(u,pc,size,ctx):
            nonlocal saved
            if saved and pc==saved[0]:
                u.mem_write(saved[1],saved[2])
                saved=None
        def enter(u,pc,size,ctx):
            nonlocal saved
            if cpu.generation!=907 or u.reg_read(UC_ARM_REG_R2)!=2 or u.reg_read(UC_ARM_REG_R3):
                return
            sp=u.reg_read(UC_ARM_REG_SP)
            wait=bytes(u.mem_read(sp,4))
            if int.from_bytes(wait,'little')!=96*84:
                return
            ret=u.reg_read(UC_ARM_REG_LR)&~1
            assert saved is None
            saved=(ret,sp,wait)
            if ret not in returns:
                returns.add(ret)
                u.hook_add(UC_HOOK_CODE,restore,begin=ret,end=ret)
            changed.append(cpu.clock)
            u.mem_write(sp,bytes(4))
        pc=cpu.syms['nes_cost474_pause']
        cpu.u.hook_add(UC_HOOK_CODE,enter,begin=pc,end=pc)

    tag='883-only907'
    with patch.object(runtime,'__init__',attach),patch.object(runtime,'call',step):
        try:
            run(temp,2,work,tag,'dense')
        except Done:
            pass
        else:
            raise AssertionError('expected complete prefix through 910')
    new=temp/f'nes-tile821-demo-jointmirror-p2-{tag}'
    ref=temp/'nes-tile821-demo-jointmirror-p2-882-direct'
    assert changed
    def prefix(d):
        return [e for e in load(d/'events.json') if e.get('opcode') and e['clock'] <= changed[0]]
    assert prefix(new)==prefix(ref)
    out={'changed_pause_calls':changed,'matched_SPI_prefix':len(prefix(new))}
    for key,d in [('before',ref),('after',new)]:
        visible=[r for r in window(d) if r['event']=='reveal' and 907<=r['g']<=910]
        assert len(visible)==4
        out[key]=dict(display=[[r['g'],r['frame'],r['line']] for r in visible],capture=capture(d,910))
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','work','out'):
        p.add_argument(name,type=lambda x:Path(x).resolve())
    a=p.parse_args()
    a.out.write_text(json.dumps(control(a.temp,a.work),indent=2)+'\n')
