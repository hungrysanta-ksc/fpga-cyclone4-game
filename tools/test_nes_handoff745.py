# SPDX-License-Identifier: MIT
"""Matched-prefix diagnostic. Execute 727's real Thumb blocks in a different order after map completion."""
import sys
import struct
from unittest.mock import patch
from check_nes_game478 import UC_ARM_REG_PC, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_SP
from nes_raw506 import once, sha
from test_nes_raw506_joint import Runtime
import test_nes_arm745 as joint


def branch(source, dest):
    # Thumb-2 B.W. Relocated branches execute on the measured ARM timeline.
    offset = (dest-source-4) & 0x1ffffff
    sign = offset >> 24
    j1 = 1 ^ sign ^ ((offset >> 23) & 1)
    j2 = 1 ^ sign ^ ((offset >> 22) & 1)
    return struct.pack('<HH', 0xf000 | sign << 10 | (offset >> 12 & 1023),
                       0x9000 | j1 << 13 | j2 << 11 | (offset >> 1 & 2047))


def controlled(original, reserve=False, input_first=False):
    def init(cpu, args, link):
        original(cpu,args,link)
        assert sha(args.arm/'obj-nes-100/firmware.stm')=='523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655'
        state='stock'
        reserved=False
        post_map,check_oam,scroll,guard=0x801e9f0,0x801eaf2,0x801eb3a,0x801ea02
        gate=0x807f800
        for i,dest in enumerate((check_oam,post_map,scroll,guard+2)):
            at=gate+4*i
            cpu.u.mem_write(at,branch(at,dest))
        # The isolated service variant runs the same native bounded wait as
        # the linked --service candidate, on the unmodified prefix. SP+16 is
        # the compiler's 719 deadline, and R9 holds its starting timestamp.
        progress=0x801ea86
        allowance=gate+32
        arm=bytearray(struct.pack('<H',0xb507))  # push r0-r2,lr, keep alignment
        call=bytearray(branch(allowance+len(arm),0x80194bc))
        call[3]|=0x40  # BL to nes_cost471_now
        arm.extend(call)
        arm.extend(struct.pack('<11H',0x4649,0x1a40,0x21bc,0x0209,0x1840,0x9908,
                               0x4288,0xd200,0x9008,0xe8bd,0x4007))
        arm.extend(branch(allowance+len(arm),progress+2))
        cpu.u.mem_write(allowance,bytes(arm))
        cpu.u.mem_write(gate+16,branch(gate+16,progress+2))
        # 727's checked E8 descriptor lives on this poll stack. Execute the
        # original bounded wait before the original checked map drain. Both
        # error exits branch to the real fail(p,5) before the submit point.
        poll_input=0x801f0f2
        service=gate+128
        block=bytearray(cpu.u.mem_read(0x801f108,12))
        assert block[-2:]==bytes.fromhex('0028')
        def checked():
            block.extend(struct.pack('<H',0xd101))  # successful call skips the failure branch
            block.extend(branch(service+len(block),0x801f08a))
        checked()
        block.extend(bytes.fromhex('606a6946'))  # window and stack receipt buffer
        call=bytearray(branch(service+len(block),0x80219b2))
        call[3]|=0x40
        block.extend(call)
        block.extend(bytes.fromhex('0028'))
        checked()
        block.extend(branch(service+len(block),0x801f116))
        cpu.u.mem_write(service,bytes(block))
        expected={post_map:'2368',check_oam:'2946',scroll:'b6f8',guard:'24d1'}
        if input_first:expected[poll_input]='6946'
        if reserve:expected[progress]='e2d1'
        for at,hexbytes in expected.items():
            assert bytes(cpu.u.mem_read(at,2))==bytes.fromhex(hexbytes)
        def value(addr,n):return int.from_bytes(cpu.u.mem_read(addr,n),'little')
        def jump(index):
            cpu.events.append(dict(event='handoff745',generation=cpu.generation,clock=cpu.clock,state=state))
            cpu.u.reg_write(UC_ARM_REG_PC,(gate+4*index)|1)
        def edge(u,pc,size,userdata):
            nonlocal state,reserved
            # Restrict the intervention to the requested experiment; the full-link
            # variant beside it pays the cost of general admission from cold start.
            if cpu.irq or cpu.generation!=957:return
            if pc==post_map and state=='stock':
                plan=value(u.reg_read(UC_ARM_REG_R4),4)
                layout=cpu.layout['nes_plan200']
                desc=bytes(u.mem_read(plan+layout['bulk'],12))
                window=value(plan+layout['window'],4)
                assert value(plan+layout['bulk_valid'],1) and desc[:4]==bytes((1,0,48,0))
                assert value(window+cpu.layout['nes_sink_window184']['last']+1,1)==2
                state='checking';jump(0)
            elif pc==scroll and state=='checking':
                # Reached only through same635, both bank records, a real checked
                # E8 descriptor, E0 receipt/credit, OBJ and successful OAM issue.
                state='packing';jump(1)
            elif pc==guard and state=='packing':
                # Enter the existing periodic budget for the original final map.
                jump(3)
            elif pc==poll_input and state=='checking':
                stack=u.reg_read(UC_ARM_REG_SP)
                descriptor=bytes(u.mem_read(stack+18,12))
                assert descriptor[:4]==bytes((1,1,32,1))
                cpu.events.append(dict(event='input745',generation=cpu.generation,clock=cpu.clock))
                u.reg_write(UC_ARM_REG_PC,service|1)
            elif pc==progress and state=='packing' and u.reg_read(UC_ARM_REG_R3)==8:
                if reserved:jump(4)
                else:
                    reserved=True
                    cpu.events.append(dict(event='reserve745',generation=cpu.generation,clock=cpu.clock))
                    u.reg_write(UC_ARM_REG_PC,allowance|1)
            elif pc==check_oam and state=='packing':
                state='sent';jump(2)
        for at in expected:cpu.u.hook_add(UC_HOOK_CODE,edge,begin=at,end=at)
    return init


def arm_late(original):
    def edit(script,client):
        s=original(script,client)
        start='checkedMem527(function()\n if not installed745 then'
        stop='end,emu.callbackType.exec,0x7e2000)'
        s=once(s,start,'local function enable745()\n if not installed745 then')
        s=once(s,stop,'end')
        return once(s,' if pb(0)==7 then tile=tilePayload',
                    ' if pb(0)==7 and pb(1)==1 and pw(14)==288 then enable745() end\n if pb(0)==7 then tile=tilePayload')
    return edit


if __name__=='__main__':
    reserve='--reserve' in sys.argv
    if reserve:sys.argv.remove('--reserve')
    input_first='--input-first' in sys.argv
    if input_first:sys.argv.remove('--input-first')
    with patch.object(Runtime,'__init__',controlled(Runtime.__init__,reserve,input_first)),patch.object(joint,'instrument',arm_late(joint.instrument)):
        joint.run()
