"""Time the actual 951 input block on both sides of the per-run optimization."""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_retire878_once as parent
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                              UC_ARM_REG_R4, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R11,
                              UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_XPSR)


def replay(temp,phase,work,fast,short_wait=False):
    ref=work.parent/'nes-table877-stable'
    block=bytes.fromhex(json.loads((temp/'nes-ack861/sender-demo/sender.json').read_bytes())['951'][-3]['wire'])
    assert len(block)==117
    # Leaf has only internal relative branches and uses the ordinary ARM ABI.
    # Its full machine code, including counter updates, executes on the live CPU.
    fw=(work/'link-credit/src/obj-nes-100/firmware.stm').read_bytes()
    leaf=fw[0x10ac2:0x10b40]
    assert hashlib.sha256(leaf).hexdigest()=='f847e7d3893dbbd01499faecd83aee64627d895f5d006a1680fc20c2ba03fd76'
    assert not short_wait or fast
    mode='retry96' if short_wait else ('run' if fast else 'original')
    runtime=parent.dense.joint.Runtime
    init=runtime.__init__
    marks={}
    def attach(cpu,args,link):
        init(cpu,args,link)
        u=cpu.u
        active_receiver=None
        dst=0x08072000
        assert not any(u.mem_read(dst,len(leaf)))
        u.mem_write(dst,leaf)
        def mark(name):
            assert name not in marks,name
            marks[name]=dict(clock=cpu.clock,instructions=cpu.instructions)
        def listen(pc,callback):
            u.hook_add(UC_HOOK_CODE,callback,begin=pc,end=pc)
        def record_return(name,receiver=None):
            pc=u.reg_read(UC_ARM_REG_LR)&~1
            def returned(u,at,size,ctx):
                if name not in marks:
                    if receiver is not None:
                        assert u.reg_read(UC_ARM_REG_R0)==1
                    mark(name)
                    if receiver is not None:
                        n=cpu.layout['nes_native165']['size']
                        marks[name]['state_sha256']=hashlib.sha256(u.mem_read(receiver,n)).hexdigest()
            listen(pc,returned)
        def crc_begin(u,at,size,ctx):
            if cpu.input_generation==951 and u.reg_read(UC_ARM_REG_R2)==len(block) and bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),len(block)))==block:
                mark('crc_begin');record_return('crc_end')
        def packet_begin(u,at,size,ctx):
            nonlocal active_receiver
            if cpu.input_generation==951 and u.reg_read(UC_ARM_REG_R3)==len(block) and bytes(u.mem_read(u.reg_read(UC_ARM_REG_R2),len(block)))==block:
                active_receiver=u.reg_read(UC_ARM_REG_R0)
                mark('packet_begin');record_return('packet_end',active_receiver)
        def active():
            return 'packet_begin' in marks and 'packet_end' not in marks
        def logical(u,at,size,ctx):
            if not active():return
            kind,index=u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R3)
            if kind==7 and index==4:mark('meta_begin')
            if kind==4 and index in (0,185):mark(f'run{index}_begin')
        def tail(u,at,size,ctx):
            if not active() or u.reg_read(UC_ARM_REG_R7)!=0:return
            start,n=u.reg_read(UC_ARM_REG_R9),u.reg_read(UC_ARM_REG_R8)
            assert (start,n) in ((0,184),(185,39))
            mark(f'run{start}_checked')
            if fast:
                # Original loop has just checked and stored its first line.
                # Its initial uint64 still occupies the outgoing stack slot.
                receiver=u.reg_read(UC_ARM_REG_R11)
                off=cpu.layout['nes_native165']['raster']+start*8
                assert u.mem_read(receiver+off,8)==u.mem_read(u.reg_read(UC_ARM_REG_SP),8)
                for reg,val in ((UC_ARM_REG_R0,receiver),(UC_ARM_REG_R1,start),(UC_ARM_REG_R2,n),
                                (UC_ARM_REG_LR,0x0801d255),(UC_ARM_REG_PC,dst|1)):
                    u.reg_write(reg,val)
        def completed(u,at,size,ctx):
            if active():
                for start in (0,185):
                    key=f'run{start}'
                    if key+'_checked' in marks and key+'_end' not in marks:mark(key+'_end')
        listen(cpu.syms['crc_xmodem_block'],crc_begin)
        listen(cpu.syms['nes_native165_packet'],packet_begin)
        listen(cpu.syms['logical_record'],logical)
        listen(0x0801d234,tail)
        listen(0x0801d254,completed)
        if short_wait:
            # Change only the threshold of the existing STOP-checked quiet loop
            # after the receiver reached COMPLETE. The real E0 still owns ACK.
            pause=cpu.syms['nes_cost474_pause'] & ~1
            branch=pause+0x62
            assert bytes(u.mem_read(branch-4,6)).hex()=='b3f5285ff4d3'
            def compare(u,at,size,ctx):
                if cpu.generation!=950 or active_receiver is None or u.reg_read(UC_ARM_REG_R4)!=2:return
                if u.mem_read(active_receiver+cpu.layout['nes_native165']['state'],1)!=bytes([2]):return
                flags=u.reg_read(UC_ARM_REG_XPSR) & ~(1<<29)
                u.reg_write(UC_ARM_REG_XPSR, flags | (int(u.reg_read(UC_ARM_REG_R3)>=84*96)<<29))
            listen(branch,compare)
    original=parent.run
    def tagged(temp,phase,work,tag,clip):
        return original(temp,phase,work,'879-'+mode,clip)
    with patch.object(runtime,'__init__',attach),patch.object(parent,'run',tagged):
        parent.replay(temp,phase,ref)
    assert all(k in marks for k in ('crc_end','run0_end','run185_end','meta_begin','packet_end'))
    (work/f'{mode}-p{phase}.json').write_text(json.dumps(marks,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('phase',type=int)
    p.add_argument('work',type=lambda s:Path(s).resolve())
    p.add_argument('--fast',action='store_true')
    p.add_argument('--short-wait',action='store_true')
    replay(**vars(p.parse_args()))
