"""Execute the linked FF3 checkpoint service and FatFS on a sector-backed SD image."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from check_nes_game478 import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_MCLASS, UC_MODE_THUMB
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
                               UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_XPSR)


def fat16():
    disk = bytearray(16384*512)
    disk[:11] = b'\xeb\x3c\x90MSDOS5.0'
    struct.pack_into('<HBHBHHBHHH', disk, 11, 512, 1, 1, 2, 512, 16384, 0xf8, 64, 32, 64)
    disk[54:62] = b'FAT16   '
    disk[510:512] = b'\x55\xaa'
    for sector in (1,65):
        disk[sector*512:sector*512+4] = b'\xf8\xff\xff\xff'
    return disk


def crc8(data):
    crc=0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc=((crc<<1) ^ (7 if crc & 128 else 0)) & 255
    return crc


class Machine:
    def __init__(self,src,disk):
        self.u=u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        u.mem_map(0x08000000,0x80000)
        u.mem_map(0x20000000,0x10000)
        obj=src/'obj-nes-100'
        flash=(obj/'firmware.stm').read_bytes()
        with (obj/'sd2snes.elf').open('rb') as f:
            elf=ELFFile(f)
            for seg in elf.iter_segments():
                if seg['p_type']=='PT_LOAD' and seg['p_filesz']:
                    start=seg['p_paddr']-0x0800c000
                    assert flash[start:start+seg['p_filesz']]==seg.data()
                    u.mem_write(seg['p_vaddr'],seg.data())
            self.sym={s.name:s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
        self.disk=disk
        self.flags=self.word=self.count=self.bat_index=self.writes=0
        self.battery=bytearray(8192)
        self.state=bytearray(21264)
        self.free=65536
        self.drain_steps=0
        self.pending_frames=0
        self.hooks={}
        for name in ('disk_initialize','disk_status','disk_ioctl','disk_read','disk_write',
                     'checkpoint_exchange','nes_runtime165_step','get_fattime','printf'):
            address=self.sym[name]&~1
            self.hooks[name]=u.hook_add(UC_HOOK_CODE,self.hook,name,address,address)
        u.mem_write(0x0807ffe0,b'0:\0')
        assert self.call('f_mount',self.sym['fatfs'],0x0807ffe0,1)==0
        u.mem_write(self.sym['nes_board_id'],b'\x7d')
        u.mem_write(self.sym['gpio_owned'],b'\1')
        self.rom(0x7169ada2)

    def rom(self,crc):
        self.u.mem_write(self.sym['nes_content_crc'],struct.pack('<I',crc))

    def hook(self,u,pc,size,name):
        a,b,c,d=(u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
        ret=0
        if name in ('disk_read','disk_write'):
            assert a==0 and d>0 and (c+d)*512<=len(self.disk)
            start,end=c*512,(c+d)*512
            if name=='disk_read':
                u.mem_write(b,bytes(self.disk[start:end]))
            else:
                assert self.flags&3==3 and u.mem_read(self.sym['ff3_writing_save'],1)==b'\1'
                self.disk[start:end]=u.mem_read(b,end-start)
                self.writes+=d
        elif name=='nes_runtime165_step':
            assert self.flags==1 and self.pending_frames
            self.drain_steps+=1
            self.pending_frames-=1
            if not self.pending_frames:self.flags=3
            ret=1
        elif name=='checkpoint_exchange':
            tx=bytes(u.mem_read(a,13))
            assert tx[0]==0x59 and tx[-1]==crc8(tx[:-1])
            op,idx=tx[1],int.from_bytes(tx[2:4],'big')
            pending=self.flags&4
            address=self.word if pending else self.bat_index
            rx=bytearray(13)
            rx[:4]=bytes((0x59,self.flags))+address.to_bytes(2,'big')
            if pending and not (self.flags&8):
                rx[4:12]=self.state[8*self.word:8*self.word+8]
            if self.flags&64: rx[4]=self.battery[address]
            rx[12]=crc8(rx[:12]);rx[0]=0
            u.mem_write(b,bytes(rx))
            if op==1:self.flags|=1 if self.pending_frames else 3
            elif op==2:self.flags=0
            elif op in (3,4):
                assert self.flags&3==3
                self.word=int(op==3);self.flags=23|(8 if op==4 else 0);self.count=0
            elif op in (5,6):
                assert pending and idx==self.word and (op==6)==bool(self.flags&8)
                if op==5:assert tx[4:12]==self.state[8*idx:8*idx+8]
                else:self.state[8*idx:8*idx+8]=tx[4:12]
                self.count+=1
                if self.count==2658:self.flags=35
                else:self.word=(self.word+1)%2658
            elif op in (7,8):
                assert idx<8192 and self.flags&3==3
                self.bat_index=idx
                if op==8:self.battery[idx]=tx[4]
                self.flags=67 if op==7 else 3
            else:assert op==0
            ret=1
        u.reg_write(UC_ARM_REG_R0,ret)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

    def call(self,name,*args,live=False,instructions=120000000):
        top=self.sym['__stack']-(31368 if live else 0)
        low=self.sym['__bss_end__']
        self.u.mem_write(low,b'\xad'*(top-low))
        sentinel=0x0807fff0
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):
            self.u.reg_write(r,v)
        self.u.reg_write(UC_ARM_REG_SP,top)
        self.u.reg_write(UC_ARM_REG_XPSR,0x01000000)
        self.u.reg_write(UC_ARM_REG_LR,sentinel|1)
        self.u.emu_start(self.sym[name]|1,sentinel,count=instructions)
        assert self.u.reg_read(UC_ARM_REG_PC)==sentinel,name
        if live:
            region=bytes(self.u.mem_read(low,top-low))
            left=len(region)-len(region.lstrip(b'\xad'))
            assert left>0,'collided with firmware globals'
            self.free=min(self.free,left)
        return self.u.reg_read(UC_ARM_REG_R0)


def check_sector_gate(src):
    """Run the real native sector loop, substituting the SD electrical interface."""
    m=Machine(src,fat16())
    m.u.hook_del(m.hooks['disk_write'])
    m.u.mem_map(0x42410000,4096)  # SD card-detect GPIO bit-band page
    def byte(name,value): m.u.mem_write(m.sym[name],bytes([value]))
    byte('disk_state',2)
    byte('ccs',1)
    byte('phase094',4)  # DISPLAY146
    reset=False
    revoke_after=0
    sectors=[]
    def device(u,pc,size,name):
        nonlocal reset
        result=0
        if name=='cmd_fast':
            assert u.reg_read(UC_ARM_REG_R0)==24
            sectors.append(u.reg_read(UC_ARM_REG_R1))
            result=6
        elif name=='send_datablock':
            if len(sectors)==revoke_after: reset=True
        elif name=='get_snes_reset': result=int(reset)
        elif name in ('nes_diag_active','nes_cf86_check094','nes_diag_sd_response'): result=1
        u.reg_write(UC_ARM_REG_R0,result)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for name in ('cmd_fast','send_datablock','get_snes_reset','nes_diag_active',
                 'nes_cf86_check094','nes_diag_sd_response','nes_return_failed','nes_return_log_allowed'):
        addr=m.sym[name]&~1
        m.u.hook_add(UC_HOOK_CODE,device,name,addr,addr)
    def write(): return m.call('sdn_write',0,0x20008000,300,2)
    assert write()==2 and not sectors  # game running normally
    byte('ff3_writing_save',1)
    for name,value,original in [('nes_board_id',0x7c,0x7d),('gpio_owned',0,1),('phase094',0,4)]:
        byte(name,value)
        assert write()==2 and not sectors
        byte(name,original)
    reset=True
    assert write()==2 and not sectors
    reset=False
    assert write()==0 and sectors==[300,301]
    sectors.clear()
    revoke_after=1
    assert write()==2 and sectors==[300]  # reset between adjacent sectors
    return len(sectors)


def check(src):
    disk=fat16()
    m=Machine(src,disk)
    checkpoint=bytearray((i*31+i//256)&255 for i in range(21264))
    checkpoint[:8]=bytes.fromhex('00000000c4140000')
    checkpoint[14]&=252
    battery=bytes((i*7+i//128)&255 for i in range(8192))
    m.state[:]=checkpoint;m.battery[:]=battery
    # A live receiver causes the actual ARM caller to keep servicing a
    # pending display even after the hardware blocks the next capture.
    m.u.mem_write(m.sym['native_runtime165'],struct.pack('<I',0x20008000))
    m.pending_frames=2
    for slot in (0,2):
        assert m.call('nes_menu_state_io',slot,0,live=True)==1,('save',slot)
        assert m.call('nes_menu_state_resume')==1
    power=Machine(src,disk)
    assert m.drain_steps==2
    assert power.call('nes_menu_state_io',0,1,live=True)==1 and power.battery==battery
    assert power.call('nes_menu_state_resume')==1
    power.rom(0x7169ada3)
    assert power.call('nes_menu_state_io',2,1,live=True)==0 and power.flags==0
    power.rom(0x7169ada2)
    assert power.call('nes_menu_state_io',2,1,live=True)==1 and power.state==checkpoint
    assert power.call('nes_menu_state_resume')==1 and power.writes==0
    return dict(firmware_sha256=hashlib.sha256((src/'obj-nes-100/firmware.stm').read_bytes()).hexdigest(),
                battery_bytes=len(battery),state_bytes=len(checkpoint),sectors_written=m.writes,
                pending_display_steps=m.drain_steps,sectors_written_before_reset_stop=check_sector_gate(src),
                free_stack_observed_B=min(m.free,power.free),caller_stack_reserved_B=31368,
                boundary='linked ARM/FatFS, modeled sector device and 0x59 peripheral')


def checkpoint_roundtrip(src, rom_crc):
    """Hand a live RTL checkpoint to two successive linked MCU instances."""
    words = Path('core-state.hex').read_text().splitlines()
    assert len(words) == 2658
    image = b''.join(int(word, 16).to_bytes(8, 'little') for word in words)
    from check_ff3_menu_arm import dispatch
    restored=bytearray()
    result=dispatch(src,rom_crc,image,restored)
    words=(restored[i:i+8] for i in range(0,len(restored),8))
    Path('restarted-state.hex').write_text(''.join(f"{int.from_bytes(w,'little'):016x}\n" for w in words))
    print(f"FF3 FAT16 menu checkpoint via two ARM boots {result}",flush=True)



if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('report',type=Path)
    args=p.parse_args()
    result=check(args.src)
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(result)
