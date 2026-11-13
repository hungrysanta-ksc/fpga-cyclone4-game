# SPDX-License-Identifier: MIT
"""Compare all CRC accumulator/next-byte pairs with the actual Thumb code."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1
from elftools.elf.elffile import ELFFile
from nes_raw506 import sha


def check(probe):
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    boot=0x08000000
    end=boot+0x7ff00
    u.mem_map(boot,0x80000)
    buf=0x20000000
    u.mem_map(buf,4096)
    with probe.open('rb') as f:
        elf=ELFFile(f);code=elf.get_section_by_name('.text')
        u.mem_write(code['sh_addr'],code.data())
        entry=next(s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='final_crc747')
    table=[]
    for value in range(256):
        x=value
        for _ in range(8):x=((x<<1)^(7 if x&128 else 0))&255
        table.append(x)
    assert len(set(table))==256
    for a in range(256):
        for b in range(256):
            u.mem_write(buf,bytes((a,b)))
            u.reg_write(UC_ARM_REG_R0,buf);u.reg_write(UC_ARM_REG_R1,2)
            u.reg_write(UC_ARM_REG_LR,end|1)
            u.emu_start(entry|1,end,count=50)
            assert u.reg_read(UC_ARM_REG_R0)==table[table[a]^b],(a,b)
    return dict(transitions=65536,polynomial=7,initial=0,probe=sha(probe))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('probe','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(check(a.probe),indent=2)+'\n')
