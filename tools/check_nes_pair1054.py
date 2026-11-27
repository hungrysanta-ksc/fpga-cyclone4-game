"""Run the final ARM preloader on FatFS with a byte-addressed model of the menu mapper."""
from pathlib import Path
import json
import struct
import zlib
from check_ff3_sd1043 import Machine, fat16, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_LR
from prepare_nes_pair1054 import WORK

def drive(raw):
    disk=fat16()
    first=161
    blocks=(len(raw)+511)//512
    for i in range(blocks):
        for table in (1,65):
            struct.pack_into('<H',disk,table*512+2*(2+i),0xffff if i+1==blocks else i+3)
    at=129*512
    disk[at:at+11]=b'TEST    NES'
    disk[at+11]=32
    struct.pack_into('<HI',disk,at+26,2,len(raw))
    disk[first*512:first*512+len(raw)]=raw
    return disk

def stage(raw,board,inject=False):
    disk=drive(raw)
    start_disk=bytes(disk)
    m=Machine(WORK/'release/link/src',disk)
    u=m.u
    u.mem_write(m.sym['nes_board_id'],bytes([board]))
    u.mem_write(0x0807fe00,b'0:/test.nes\0')
    image=bytearray(0x240000)
    offsets=[]
    screen=[]
    resets=[]
    def hw(u,pc,size,name):
        a,b,c=(u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
        if name=='sram_writeblock':
            assert c==512 and b+c<=len(image)
            offsets.append(b)
            image[b:b+c]=u.mem_read(a,c)
        elif name=='snes_bootprint_center':
            screen.append((a,bytes(u.mem_read(b,16)).split(b'\0')[0].decode(),c))
        elif name=='snes_reset':
            resets.append(a)
        elif name=='disk_read':
            if not (inject and c>=167):
                return Machine.hook(m,u,pc,size,name)
            c=1
        u.reg_write(UC_ARM_REG_R0,c)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for name in ('sram_writeblock','snes_bootprint_center','snes_reset','disk_read'):
        if name in m.hooks:u.hook_del(m.hooks[name])
        addr=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,hw,name,addr,addr)
    ok=m.call('retail_stage1054',0x0807fe00,0x0807fd00,instructions=150000000)
    assert resets==[1] and bytes(disk)==start_disk
    if inject:
        assert not ok and 0<len(offsets)<=6
        return dict(read_error_rejected=True,completed_before_error=len(offsets))
    assert ok and screen[0][:2]==(10,'Loading NES') and screen[1][:2]==(12,'0%%')
    assert [row[2] for row in screen[2:]]==list(range(5,101,5))
    data=raw[16:]
    assert offsets==list(range(0,0x80000,512))+list(range(0x200000,0x200000+len(data)-0x80000,512))
    assert image[:0x80000]==data[:0x80000]
    for i,value in enumerate(data[0x80000:]):
        # Physical read wiring: byte address bits 2:1 -> pin, 0 -> chip, 3 -> lane.
        assert image[0x200000+16*(i//16)+2*((i%16)%8)+(i%16)//8]==value
    crc=struct.unpack('<I',u.mem_read(m.sym['nes_content_crc'],4))[0]
    assert crc==zlib.crc32(raw)
    return dict(blocks=len(offsets),bytes=len(data),crc32=f'{crc:08x}',percent_steps=len(screen)-1)

if __name__=='__main__':
    directory=Path.home()/'Downloads/test'
    kirby=next(directory.glob('Hoshi no Kirby*.nes')).read_bytes()
    ff3=next(directory.glob('Final Fantasy III*rel.DWYN*.nes')).read_bytes()
    result=dict(kirby=stage(kirby,0x7c),ff3=stage(ff3,0x7d),fault=stage(kirby,0x7c,True))
    print(result)
    (WORK/'preload.json').write_text(json.dumps(result,indent=2))
