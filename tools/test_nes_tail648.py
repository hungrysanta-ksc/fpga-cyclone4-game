"""Read-only hooks on the linked M4 for table/descriptor readiness and FIFO credit."""
import runpy
from unittest.mock import patch
from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP
from unicorn import UC_HOOK_MEM_WRITE
from test_nes_raw506_joint import Runtime
from test_nes_tail646 import watch


def clocks(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        args.trace_credit=True
        w=cpu.rt+cpu.layout["nes_native_runtime165"]["transport"]
        counters=w+cpu.layout["nes_sink_window184"]["sent"]
        assert counters+2==w+cpu.layout["nes_sink_window184"]["retired"]
        history={}
        stack_hook=[]
        def emit(event,**fields):
            sent,ret=(int.from_bytes(cpu.u.mem_read(counters+i,2),"little") for i in (0,2))
            cpu.events.append(dict(event=event,clock=cpu.clock,generation=cpu.generation,sent=sent,retired=ret,**fields))
        def stamp(u,access,addr,width,value,user):
            for i in range(width):
                history[addr+i]=cpu.clock
        def start(u,pc,size,user):
            if cpu.generation in (954,955):
                history.clear()
                stack_hook.append(u.hook_add(UC_HOOK_MEM_WRITE,stamp,begin=0x2000f000,end=0x2000ffff))
        def ready(u,pc,size,user):
            if cpu.generation not in (954,955):return
            op,section,offset=(u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
            if op!=3 and not(section==5 and offset>=1505):return
            ptr=int.from_bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP),4),"little")
            fields={}
            if op==3:
                assert stack_hook and all(ptr+i in history for i in range(168))
                fields["last_descriptor_store"]=max(history[ptr+i] for i in range(168))
                u.hook_del(stack_hook.pop())
            emit("wire_ready648",op=op,section=section,offset=offset,**fields)
        def head(u,pc,size,user):
            if cpu.generation not in (954,955):return
            p=u.reg_read(UC_ARM_REG_R1)
            h=bytes(u.mem_read(p,16))
            off=int.from_bytes(h[10:12],"little")
            if h[0]==3 or (h[1]==5 and off>=1505):
                emit("wire_head648",op=h[0],section=h[1],offset=off,seq=int.from_bytes(h[2:4],"little"))
        def retire(u,access,addr,width,value,user):
            if cpu.generation in (954,955) and value!=int.from_bytes(u.mem_read(addr,width),"little"):
                emit("credit_observed648",new_retired=value)
        def tables(u,access,addr,width,value,user):
            if cpu.generation in (954,955):
                emit("table_store648")
        region=cpu.video+cpu.layout["nes_native_video165"]["bg_keys"]+2048
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,tables,begin=region,end=region+239)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,retire,begin=counters+2,end=counters+3)
        for sym,fn in (("nes_sink212_seal",start),("packet_wire",ready),("nes_window184_enqueue",head),("nes_window184_barrier",head)):
            pc=cpu.syms[sym]
            cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
    return init


if __name__=="__main__":
    with patch.object(Runtime,"__init__",clocks(watch(Runtime.__init__))):
        runpy.run_module("test_nes_export636",run_name="__main__")
