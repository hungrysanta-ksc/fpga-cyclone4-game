"""Replay the 768 KiB progress cadence in both final ARM images with modeled FatFS."""
import argparse
import re
import struct
from pathlib import Path
from check_nes_game478 import (Machine, UC_HOOK_CODE, UC_ARM_REG_PC, UC_ARM_REG_LR,
                               UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
from package_nes_trial704 import save, digest
from prepare_nes_kirby1024 import PREVIOUS,WORK

SAMPLE=re.compile(rb'^MMC([0-9]+) seq=(\d+) stage=(\w+) bytes=(\d+) total=(\d+) elapsed_ms=(\d+) ')
def records(data):
    assert len(data)%512==0
    result=[]
    for pos in range(0,len(data),512):
        sector=data[pos:pos+512]
        m=SAMPLE.match(sector)
        assert m and int(m[2])==pos//512 and sector[-1:]==b'\n'
        result.append((m[3].decode(),int(m[4]),int(m[5])))
    return result

def replay(root,edition,physical):
    src=root/'link/src'
    m=Machine(src,bytes(128))
    m.u.mem_map(0xe000e000,0x2000)
    journal=bytearray()
    failed=False
    write_at=None
    def hook(u,pc,size,name):
        nonlocal failed,write_at
        a,b,c,d=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        ret=0
        if name=='nes_return_fail':failed=True
        if name=='nes_return_failed':ret=int(failed)
        if name in ('nes_cf86_check094','get_snes_reset','nes_diag_active','nes_return_checkpoint_enter112'):ret=1
        if name=='f_open':
            path=bytes(u.mem_read(b,80)).split(b'\0',1)[0]
            assert path==f'/sd2snes/nes-progress-mmc{edition}.txt'.encode()
            if c&8:journal.clear()
            u.mem_write(a+12,struct.pack('<I',len(journal)))
        if name=='f_lseek':
            assert b==len(journal)
            write_at=b
        if name=='f_write':
            assert c==512 and write_at==len(journal)
            journal.extend(u.mem_read(b,c));write_at=None
            u.mem_write(d,struct.pack('<I',c))
        u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    names=('nes_return_fail','nes_return_failed','nes_cf86_failed094','nes_cf86_check094','nes_diag_active','get_snes_reset',
           'nes_return_checkpoint_enter112','nes_return_checkpoint_leave112','nes_diag_ticks','nes_base_spi_sr116','nes_base_spi_cr116',
           'f_open','f_lseek','f_write','f_sync','f_close')
    for name in names:
        pc=m.syms[name];m.u.hook_add(UC_HOOK_CODE,hook,name,begin=pc,end=pc)
    def checkpoint(stage,n=0,total=0):
        addr=0x20012000;m.u.mem_write(addr,stage.encode()+b'\0')
        assert m.call('nes_checkpoint112',[addr,n,total])
    total=0xc0000
    def progress(phase,n,length=total):
        m.call('nes_checkpoint_progress112',[phase,n,length])
    assert m.call('nes_checkpoint_begin112',[])==1
    for stage in ('CSS_CHECK_NEXT','CSS_READY','OPEN_INPUT'):checkpoint(stage)
    for n in range(256,total+1,256):progress(1,n)
    progress(2,0,0);checkpoint('CONFIG_READY');checkpoint('BEGIN_LOAD',0,total)
    for n in range(0,total+1,256):progress(3,n)
    for n in range(0,total+1,256):
        progress(4,n)
        if failed:break
    if edition==1023:
        assert failed and n==414720 and records(journal)==physical
        return dict(reproduced=True,first_rejected_check_B=n,records=len(journal)//512)
    assert not failed and records(journal)[:len(physical)]==physical
    for stage in ('DISPLAY_NEXT','DISPLAY_STOPPED','STOP_START','STOP_DONE','BASE_START','BASE_FILE_OPEN_NEXT',
                  'BASE_FILE_OPENED','BASE_PINS_READY','BASE_STREAM_END','BASE_DONE_HIGH','BASE_PGM_OK',
                  'BASE_SPI_STATE_NEXT','BASE_TOKEN_NEXT','BASE_TOKEN_RESULT','BASE_DONE','MENU_COPY_START'):
        checkpoint(stage)
    for n in range(256,65537,256):progress(5,n,65536)
    checkpoint('MENU_PREPARED',65536,65536)
    out=records(journal)
    assert out[-1][0]=='MENU_PREPARED' and not failed
    return dict(records=len(out),after_128=out[128],end=out[-1],model=True,
                firmware=digest((src/'obj-nes-100/firmware.stm').read_bytes()))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('log',type=Path)
    a=p.parse_args()
    data=a.log.read_bytes();physical=records(data)
    assert len(physical)==128 and physical[-1]==('CHECK',398080,786432)
    result={'hardware_progress_sha256':digest(data),'old':replay(PREVIOUS,1023,physical),'fixed':replay(WORK,1024,physical)}
    print(result)
    save(WORK/'proof/journal.json',result)
