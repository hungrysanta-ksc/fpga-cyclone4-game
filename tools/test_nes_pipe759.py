# SPDX-License-Identifier: MIT
"""Run the linked SPI-DMA wait and planner on the same clock as the SNES FIFO."""
import runpy
import struct
from unittest.mock import patch
from test_nes_raw506_joint import ARM_HZ, MASTER, Runtime
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3

DMA=0x40026400
BOTH_DONE=(1<<27)|(1<<5)
RETURN=0x0807ff80

def install(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        if 'nes182_run' not in cpu.syms or 'nes_map759_step' not in cpu.syms:return
        def registers(u,access,addr,size,value,user):
            transfer=getattr(cpu,'wire759',None)
            if transfer is None:return
            if addr==DMA:
                # Polling an empty queue performs no useful work. Sleep only
                # to the next IRQ or TC edge; neither returns queue credit.
                if transfer['polls'] and not int.from_bytes(u.mem_read(cpu.data_symbols['pending759']+8,4),'little'):
                    cpu.clock=max(cpu.clock,min(cpu.next_irq,transfer['end']))
                transfer['polls']+=1
            left=max(0,min(len(transfer['tx']),int((transfer['end']-cpu.clock)*2625000/(8*MASTER)+0.999999)))
            for at,val in ((DMA,BOTH_DONE if not left else 0),(DMA+0x14,left),(DMA+0x5c,left)):
                u.mem_write(at,struct.pack('<I',val))
        cpu.u.hook_add(UC_HOOK_MEM_READ,registers,begin=DMA,end=DMA+0x5f)
    return init

def intercept(original):
    def hook(cpu,u,at,size,user):
        if not cpu.live or cpu.irq or at not in (cpu.spi,RETURN):
            return original(cpu,u,at,size,user)
        if cpu.clock>=cpu.next_irq:
            return original(cpu,u,at,size,user)
        if at==RETURN:
            # Returning from actual nes182_run means that the TC status and
            # both zero NDTR counters have been checked on the ARM.
            w=cpu.wire759
            assert cpu.clock>=w['end'] and u.reg_read(UC_ARM_REG_R0)==1
            cpu.clock=cpu.link.rpc(cpu.clock+cpu.driver_extra[0xe1]/2)
            cpu.clock=cpu.link.accept(w['tx'],cpu.clock)
            n=len(w['tx']);cpu.wire_B['0xe1']=cpu.wire_B.get('0xe1',0)+n
            cpu.events.append(dict(event='SPI',generation=cpu.generation,opcode='0xe1',
                              packet_opcode=2,bytes=n,start=w['start'],clock=cpu.clock,
                              DMA_start759=w['wire_start'],DMA_end759=w['end'],polls759=w['polls']))
            u.mem_write(w['rx'],bytes(n));cpu.wire759=None
            u.reg_write(UC_ARM_REG_PC,w['lr']);return
        n=u.reg_read(UC_ARM_REG_R3)
        ptr=u.reg_read(UC_ARM_REG_R1)
        if 'nes_map759_step' not in cpu.syms or n<19 or bytes(u.mem_read(ptr,3))!=bytes((0xe1,2,2)):
            return original(cpu,u,at,size,user)
        assert not getattr(cpu,'wire759',None)
        tx=bytes(u.mem_read(ptr,n));cpu.instructions+=1;cpu.clock+=cpu.a.cpi*MASTER/ARM_HZ
        start=cpu.link.rpc(cpu.clock);cpu.clock=start+cpu.driver_extra[0xe1]/2
        cpu.wire759=dict(tx=tx,start=start,rx=u.reg_read(UC_ARM_REG_R2),lr=u.reg_read(UC_ARM_REG_LR),
                         wire_start=cpu.clock,end=cpu.clock+n*8*MASTER/2625000,polls=0)
        u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_LR,RETURN|1)
        u.reg_write(UC_ARM_REG_PC,cpu.syms['nes182_run']|1)
    return hook

if __name__=='__main__':
    with patch.object(Runtime,'__init__',install(Runtime.__init__)),patch.object(Runtime,'hook',intercept(Runtime.hook)):
        runpy.run_module('test_nes_tail758',run_name='__main__')
