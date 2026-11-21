"""Exercise frame-scoped progress reset and a stale BEGIN receipt on the final ARM link."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import Machine, ELFFile, crc
from check_nes_hardware494_termination import member_offset
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3


def offsets(src, name):
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        return next({c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}
                    for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
                    if d.tag=='DW_TAG_structure_type' and 'DW_AT_byte_size' in d.attributes and
                    d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==name.encode())


def drain_guards(src):
    m=Machine(src,bytes(128))
    fields=offsets(src,'nes_sink_window184')
    address,guard,transfer=0x20012000,0x0807ffc4,0x0807ffc8
    header=bytes.fromhex('0a02300021000000a803')
    def callback(u,pc,size,ctx):
        if pc==transfer:
            assert bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),1))==b'\xe0'
            assert u.reg_read(UC_ARM_REG_R3)==20
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(reply))
        u.reg_write(UC_ARM_REG_R0,int(not stopped))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for pc in (guard,transfer):
        m.u.hook_add(UC_HOOK_CODE,callback,begin=pc,end=pc)
    results={}
    for name in ('valid','crc','generation','live','seal_as_map','stop'):
        m.u.mem_write(address,bytes(128))
        for field,value,n in [('transfer',transfer|1,4),('guard',guard|1,4),('poll_limit',1,4),
                              ('sent',1,2),('initialized',1,1),('ever_sent',1,1)]:
            m.u.mem_write(address+fields[field],value.to_bytes(n,'little'))
        m.u.mem_write(address+fields['last'],header)
        reply=bytearray.fromhex('00f70a00010001000a')+header[2:]+bytes.fromhex('659a00')
        if name=='generation':
            reply[15]^=1
        if name=='live':
            reply[2]=9
            reply[6]=0
        if name=='seal_as_map':
            reply[8]=3
        reply[-1]=crc(reply[1:19],8,7,0)^int(name=='crc')
        stopped=name=='stop'
        accepted=m.call('nes_window184_drain',[address,address+128])
        assert accepted==int(name=='valid'),name
        results[name]=bool(accepted)
    return results


def check(src):
    m=Machine(src,bytes(128))
    fields=offsets(src,'nes_native_sink165')
    sink=0x20012000
    marker=sink+fields['strip_dma_seen']
    callback=0x0807ffc0
    corrupt=False
    def reply(u,pc,size,ctx):
        b=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),16))
        assert b[:2]==bytes((1,0))
        ack=bytearray([0,1])+b[2:10]+bytes((0x65,0x9a))
        if corrupt:ack[4]^=1
        u.mem_write(u.reg_read(UC_ARM_REG_R3),bytes(ack))
        u.reg_write(UC_ARM_REG_R0,1)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    m.u.hook_add(UC_HOOK_CODE,reply,begin=callback,end=callback)
    cases={}
    for name in ('cold','next_bank','stale'):
        corrupt=name=='stale'
        m.u.mem_write(marker,b'\x01')
        m.call('nes_sink165_reset',[sink,callback|1,0])
        assert bytes(m.u.mem_read(marker,1))==bytes(1)
        prior=int(name!='cold')
        m.u.mem_write(sink+fields['serial'],prior.to_bytes(4,'little'))
        m.u.mem_write(sink+fields['displayed'],bytes([prior]))
        r=m.layout['nes_resident211']
        for key,val,width in [('open',1,1),('serial',prior+1,4),('displayed',prior,1),
                              ('generation',936,2),('target',prior,1),('epoch',1,4)]:
            m.u.mem_write(m.resident+r[key],val.to_bytes(width,'little'))
        m.u.mem_write(marker,b'\x01')
        ok=m.call('nes_sink212_begin',[sink,m.resident])
        assert ok==int(not corrupt) and bytes(m.u.mem_read(marker,1))==bytes(1)
        cases[name]=dict(accepted=bool(ok),progress_cleared=True)
    return dict(begin=cases,strip_E0=drain_guards(src))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.src),indent=2)+'\n')
