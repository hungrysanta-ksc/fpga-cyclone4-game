"""Read-only actual M4 readiness/credit boundaries; no simulated time or bytes altered."""
import hashlib
import runpy
from unittest.mock import patch
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_PC
from unicorn import UC_HOOK_MEM_WRITE
from test_nes_raw506_joint import Runtime

TARGET={905,906,911,951,952,953,954,955,956,957}


def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        pending={};returns=set();serial=0;last={};sealed={};tracking=None
        layout=cpu.layout['nes_native_video165']
        ranges={k:(cpu.video+layout[k],n) for k,n in (('oam',544),('cgram',512),('hdma',1121))}
        ranges.update(patch_chr=(cpu.video+layout['patch'],2048),patch_tables=(cpu.video+layout['patch']+2048,243),patch_sizes=(cpu.video+layout['patch']+2292,6))
        transport=cpu.rt+cpu.layout['nes_native_runtime165']['transport']
        counters=transport+cpu.layout['nes_sink_window184']['sent']
        def record(event,**fields):
            cpu.events.append(dict(event=event,generation=cpu.generation,clock=cpu.clock,**fields))
        def snapshot():
            return {k:bytes(cpu.u.mem_read(addr,n)) for k,(addr,n) in ranges.items()}
        def writes(u,access,address,size,value,user):
            if tracking!=cpu.generation or tracking not in TARGET:return
            for name,(addr,n) in ranges.items():
                lo,hi=max(address,addr),min(address+size,addr+n)
                if lo>=hi:continue
                data=value.to_bytes(size,'little')[lo-address:hi-address]
                if name in sealed:
                    assert data==sealed[name][lo-addr:hi-addr],('mutated after planner',tracking,name,hex(address))
                for pos in range(lo-addr,hi-addr):last[name][pos]=cpu.clock
        def credit(u,access,address,size,value,user):
            if cpu.generation not in TARGET:return
            if address<=counters+2 and address+size>=counters+4:
                old=int.from_bytes(u.mem_read(counters+2,2),'little')
                new=int.from_bytes(value.to_bytes(size,'little')[counters+2-address:counters+4-address],'little')
                if old!=new:record('credit673',before=old,after=new,sent=int.from_bytes(u.mem_read(counters,2),'little'))
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,writes,begin=cpu.video,end=cpu.video+layout['size']-1)
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,credit,begin=counters,end=counters+3)
        def returned(u,pc,size,unused):
            nonlocal sealed
            if cpu.irq:return
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            for call in reversed(pending.pop(key,[])):
                assert call['generation']==cpu.generation
                record('return673',call=call['id'],name=call['name'],start=call['clock'],instructions=cpu.instructions-call['instructions'],result=u.reg_read(UC_ARM_REG_R0))
                if call['name']=='nes_native_video211_plan':
                    assert u.reg_read(UC_ARM_REG_R0)==1
                    sealed=snapshot()
                    hdma=int.from_bytes(u.mem_read(cpu.video+layout['hdma_size'],2),'little')
                    record('immutable673',hdma_size=hdma,fields={k:dict(last_write=max(last[k][:hdma] if k=='hdma' else last[k]),bytes=len(v),SHA256=hashlib.sha256(v).hexdigest()) for k,v in sealed.items()})
        def hook(name):
            def entered(u,pc,size,unused):
                nonlocal serial,last,sealed,tracking
                if cpu.irq or cpu.generation not in TARGET:return
                if name=='nes_native_video211_plan':
                    tracking=cpu.generation;sealed={};last={k:[0]*n for k,(_,n) in ranges.items()}
                serial+=1
                call=dict(id=serial,name=name,generation=cpu.generation,clock=cpu.clock,instructions=cpu.instructions)
                fields={}
                if name=='packet_wire':
                    sp=u.reg_read(UC_ARM_REG_SP);data,n,expanded=(int.from_bytes(u.mem_read(sp+i,4),'little') for i in (0,4,8))
                    fields=dict(op=u.reg_read(UC_ARM_REG_R1),section=u.reg_read(UC_ARM_REG_R2),offset=u.reg_read(UC_ARM_REG_R3),bytes=n,expanded=expanded,data_address=data,
                        SHA256=hashlib.sha256(bytes(u.mem_read(data,n))).hexdigest() if data and n else None)
                elif name=='nes_plan200_emit':
                    q=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),cpu.layout['nes_plan191']['size']))
                    fields=dict(plan=q.hex())
                elif name=='nes_plan200_progress':fields=dict(mode=u.reg_read(UC_ARM_REG_R1))
                record('call673',call=serial,name=name,sent=int.from_bytes(u.mem_read(counters,2),'little'),retired=int.from_bytes(u.mem_read(counters+2,2),'little'),**fields)
                ret=u.reg_read(UC_ARM_REG_LR)&~1;key=(ret,u.reg_read(UC_ARM_REG_SP))
                pending.setdefault(key,[]).append(call)
                if ret not in returns:returns.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
            return entered
        names=('nes_native_video211_plan','nes_plan200_end','nes_plan200_emit','nes_sink212_seal','packet_wire','nes_plan200_progress','nes_window184_through','nes_window184_enqueue','nes_window184_barrier','nes_window532_room','span')
        for name in names:
            pc=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,hook(name),begin=pc,end=pc)
    return init


if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_output668',run_name='__main__')
