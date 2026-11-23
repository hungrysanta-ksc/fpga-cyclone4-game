"""Compare every WCHAR against the two actual linked FatFS implementations."""
import hashlib
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_SP
from nes_arm964 import ARM,WORK


def converted(work):
    machine=Uc(UC_ARCH_ARM,UC_MODE_MCLASS|UC_MODE_THUMB)
    machine.mem_map(0x08000000,0x80000)
    machine.mem_map(0x20000000,0x20000)
    obj=work/'link/src/obj-nes-100'
    flash=(obj/'firmware.stm').read_bytes()
    machine.mem_write(0x0800c000,flash)
    with (obj/'sd2snes.elf').open('rb') as f:
        entry=ELFFile(f).get_section_by_name('.symtab').get_symbol_by_name('ff_wtoupper')[0]['st_value']
    # mov r0,r4; blx r7; strh r0,[r5]; adds r5,2; adds r4,1; cmp r4,r6; bne loop
    loop=struct.pack('<7H',0x4620,0x47b8,0x8028,0x3502,0x3401,0x42b4,0xd1f8)
    code=0x20000000
    out=code+0x1000
    machine.mem_write(code,loop)
    machine.reg_write(UC_ARM_REG_SP,0x2001ffe0)
    machine.reg_write(UC_ARM_REG_R7,entry|1)
    result=bytearray()
    for first in range(0,65536,4096):
        machine.reg_write(UC_ARM_REG_R4,first)
        machine.reg_write(UC_ARM_REG_R5,out)
        machine.reg_write(UC_ARM_REG_R6,first+4096)
        machine.emu_start(code|1,code+len(loop))
        assert machine.reg_read(UC_ARM_REG_R4)==first+4096
        result.extend(machine.mem_read(out,8192))
    return result


def check():
    reference=converted(WORK)
    actual=converted(ARM)
    assert reference==actual and actual[2*97:2*97+2]==b'A\0'
    return dict(inputs=65536,sha256=hashlib.sha256(actual).hexdigest())


if __name__=='__main__':
    print(check())
