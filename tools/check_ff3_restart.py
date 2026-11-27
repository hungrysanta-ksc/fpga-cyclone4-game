"""Verify the selected file against retained PSRAM after STOP, using the final linked loader."""
import argparse
import hashlib
import struct
import zlib
from pathlib import Path
from check_ff3_sd1043 import Machine, fat16
from check_ff3_state_reference import DIGEST
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2

def check(src, retained=False, corrupt=False):
    rom=next(p.read_bytes() for p in (Path.home()/'Downloads/test').glob('Final Fantasy III*.nes')
             if hashlib.sha256(p.read_bytes()).hexdigest()==DIGEST)
    disk=fat16()
    root=129*512;data=161*512
    disk[root:root+11]=b'GAME    NES'
    disk[root+11]=32
    struct.pack_into('<HI',disk,root+26,2,len(rom))
    disk[data:data+len(rom)]=rom
    for sector in (1,65):
        entries=(len(rom)+511)//512
        for i in range(entries):
            struct.pack_into('<H',disk,sector*512+2*(2+i),65535 if i==entries-1 else i+3)
    if corrupt:
        disk[data+len(rom)-1] ^= 1
    m=Machine(src,disk);m.rom(zlib.crc32(rom))
    m.u.mem_map(0x20010000,0x10000)
    scratch=0x20011000
    m.u.mem_write(scratch,b'0:/GAME.NES\0')
    m.u.mem_write(m.sym['ff3_next_slot'],b'\x02')
    m.u.mem_write(m.sym['__stack'],struct.pack('<II',scratch+256,scratch+257))
    m.u.mem_write(scratch+256,b'\x01\x01')
    length=len(rom)-16
    flags=0x82 if retained else 2
    commands=[]
    cursor=0
    def exchange(u,pc,size,name):
        nonlocal flags,cursor
        result=0
        if name=='nes_rom_spi_transfer':
            tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),8))
            op=tx[0];idx=int.from_bytes(tx[1:4],'big')
            if retained:commands.append(op)
            rx=bytearray(8);rx[1]=0x7d;rx[2]=flags
            if op==0x65:rx[4:7]=length.to_bytes(3,'big')
            elif op==0x66:assert flags==2; flags=0x22
            elif op==0x67:assert not retained and flags==0x22 and idx==cursor;flags=0x62
            elif op==0x6a:
                assert flags==0x62
                rx[3]=rom[16+cursor];rx[4:7]=cursor.to_bytes(3,'big')
            elif op==0x68:
                assert flags==0x62 and idx==cursor and tx[4]==rom[16+cursor]
                cursor+=1;flags=0x22
            elif op==0x69:assert cursor==idx==length;flags=0x82
            elif op==0x63:assert idx==length and (retained or cursor==length) and flags==0x82;flags=0x86
            else:raise AssertionError(hex(op))
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(rx));result=1
        u.reg_write(UC_ARM_REG_R0,result)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    if corrupt:
        # Exercise the real fail-stop state transition. Model its physical
        # reset pin and ARM interrupt-disable register in the linked binary.
        m.u.mem_map(0xe000e000,4096)
    for name in ('nes_diag_progress','nes_rom_spi_transfer') + (('snes_reset','nes_return_fail') if corrupt else ()):
        addr=m.sym[name]&~1;m.u.hook_add(UC_HOOK_CODE,exchange,name,addr,addr)
    fn=next(n for n in m.sym if n.startswith('prepare_rom893'))
    prepared=m.call(fn,scratch,scratch+16,0,scratch+1024,instructions=1200000000)
    if retained and corrupt:
        assert prepared==0 and not commands and m.call('nes_cf86_failed094')==1
        return 'PASS changed selected SD file rejected before START'
    assert prepared==1
    if retained:
        assert cursor==0 and not commands
        assert m.call('nes_rom_verified_start',scratch+128,length)==1
        assert commands==[0x65,0x63,0x65] and flags==0x86
        return 'PASS full SD file CRC, 0 redundant PSRAM reads, flags 82 -> START -> 86'
    assert cursor==length and flags==0x82
    assert m.call('nes_rom_verified_start',scratch+128,length)==1 and flags==0x86
    return f'PASS STOP flags 02 -> full selected FAT16 CRC, {length} independent PSRAM reads/ACK -> FINISH 82 -> START 86'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path);p.add_argument('report',type=Path)
    p.add_argument('--retained',action='store_true')
    a=p.parse_args();result=check(a.src,a.retained)
    if a.retained:result+='\n'+check(a.src,True,True)
    a.report.write_text(result+'\n');print(result)
