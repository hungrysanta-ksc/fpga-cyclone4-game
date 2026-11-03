# SPDX-License-Identifier: MIT
"""Execute MMC558's linked RUN/STOP branch, GPIO drive/sense, and verified restart."""
import argparse
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,
    UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R8,UC_ARM_REG_SP,UC_ARM_REG_XPSR)
from check_nes_game478 import Machine,sha,crc

TOTAL=0x60000
# PCs are inlined in nes_menu_sd_probe. These offsets are valid only for this image.
FIRMWARE='98fe5eeb2d9bfdd7b4be66bc50994b91a88229113dd8f9d4ba5aa3f7ed33f1d9'


def exercise(src,broken):
    assert sha(src/'obj-nes-100/firmware.stm')==FIRMWARE
    m=Machine(src,bytes(128));u=m.u
    for page in (0x40020000,0x42400000,0x42408000,0xe000e000):u.mem_map(page,0x1000)
    def word(addr,v):u.mem_write(addr,struct.pack('<I',v))
    mode=0x40020000;sense=0x42400200
    word(mode,1);word(sense,0);word(0x42408220,1)
    events=[];count=0;flags=0x82;released=False;end_stop=0x801b88e
    def log(kind,**kw):events.append(dict(event=kind,instructions=count,**kw))
    def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def write_gpio(cpu,access,addr,size,value,user):
        nonlocal released
        held=bool(value&1)
        word(sense,int(not held or (released and broken)))
        log('reset_drive',held=held)
        if not held:released=True
    def read_gpio(cpu,access,addr,size,value,user):
        log('reset_sense',held=int.from_bytes(u.mem_read(sense,4),'little')==0)
    u.hook_add(UC_HOOK_MEM_WRITE,write_gpio,begin=mode,end=mode)
    u.hook_add(UC_HOOK_MEM_READ,read_gpio,begin=sense,end=sense)
    from collections import deque
    pcs=deque(maxlen=20)
    def step(cpu,pc,size,user):
        nonlocal flags,count
        pcs.append(hex(pc));count+=1
        if pc==m.syms['nes_rom_spi_transfer']:
            tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),8))
            assert tx[6]==crc(tx[:6],8,7,0) and tx[7]==0xa5 and tx[5]==(tx[4]^255)
            op=tx[0];assert op in (0x65,0x63,0x64)
            if op!=0x65:assert int.from_bytes(tx[1:4],'big')==TOTAL
            log('spi',tx=tx.hex(),held=u.mem_read(sense,4)==bytes(4),flags_before=flags)
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes([0,0x7b,flags,0,6,0,0,0]))
            if op==0x64:flags=2
            if op==0x63:flags=0x86
            ret(1)
        elif pc==m.syms['native_session165']:
            # Omit the frame loop and its pre/postflight. Execute its real
            # successful display release and return into the actual STOP caller.
            log('display_session');u.reg_write(UC_ARM_REG_PC,m.syms['nes_display_enter146']|1)
        elif pc==m.syms['nes_return_delay']:log('settle',ms=u.reg_read(UC_ARM_REG_R0));ret(1)
        elif pc in (m.syms['nes_diag_active'],m.syms['fpga_get_done']):ret(1)
        elif pc in (m.syms['nes_return_log_allowed'],m.syms['nes_return_failed']):ret(0)
        elif pc==m.syms['nes_return_fail']:log('fail_latched');ret(0)
        elif pc==0x801b608 and broken:log('blocked');u.emu_stop()
        elif pc==end_stop:log('stopped_verified');u.emu_stop()
    u.hook_add(UC_HOOK_CODE,step)
    def armed():
        assert m.call('nes_cf86_enter094',[])==1 and m.call('nes_cf86_arm094',[])==1
    armed()
    # Verified image, local IO table and report at the native START call site.
    before=m.syms['nes_menu_sd_probe']+0x53a
    assert before==0x801b7be
    for reg,value in [(UC_ARM_REG_SP,0x2001d000),(UC_ARM_REG_R4,0x2000a000),(UC_ARM_REG_R5,TOTAL),
                      (UC_ARM_REG_R8,1),(UC_ARM_REG_XPSR,0x01000000)]:u.reg_write(reg,value)
    try:u.emu_start(before|1,end_stop+4,count=100000)
    except Exception as exc:raise RuntimeError((pcs,events)) from exc
    ops=lambda:[int(e['tx'][:2],16) for e in events if e['event']=='spi']
    if broken:
        assert events[-1]['event']=='blocked' and any(e['event']=='fail_latched' for e in events) and 0x64 not in ops(),events
    else:
        assert events[-1]['event']=='stopped_verified' and ops()==[0x65,0x63,0x65,0x64,0x65],events
        assert m.call('nes_cf86_finish094',[])==1
        # Fastest subsequent entry: model menu/base and reload/verification as
        # already complete under RESET, with the next image in VERIFIED READY.
        flags=0x82;armed()
        assert m.call('nes_rom_verified_start',[0x2001d068,TOTAL])==1
        assert m.call('nes_display_enter146',[])==1
        assert ops()==[0x65,0x63,0x65,0x64,0x65,0x65,0x63,0x65]
    assert all(e['held'] for e in events if e['event']=='spi')
    return events


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('arm','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(dict(firmware=FIRMWARE,normal=exercise(a.arm,False),stuck_released=exercise(a.arm,True)),indent=2)+'\n')
