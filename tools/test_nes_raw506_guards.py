# SPDX-License-Identifier: MIT
"""Linked506 input CRC/version rejection and negative PREPARE ownership."""
import argparse,json,struct
from pathlib import Path
from check_nes_game478 import Machine,encode as old_encode,sha
from nes_raw506 import encode
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR

class Guard(Machine):
    def __init__(self,path,mode):
        self.mode=mode;self.calls=[];super().__init__(path,bytes(128))
    def hook(self,u,at,size,user):
        op=None
        if at==getattr(self,'spi',0):
            n=u.reg_read(UC_ARM_REG_R3);rx=u.reg_read(UC_ARM_REG_R2);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n));op=tx[0];self.calls.append(tx.hex())
            if op==0xd3 and self.mode=='reject_prepare':
                assert tx[4]==0
                u.mem_write(rx,self.status());u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)
        if op==0xd1 and self.mode=='bad_payload_CRC':
            b=bytearray(u.mem_read(rx,n));b[-1]^=1;u.mem_write(rx,bytes(b))
        if op==0xd0 and self.mode=='bad_status_CRC':
            b=bytearray(u.mem_read(rx,n));b[-1]^=1;u.mem_write(rx,bytes(b))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','data','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);rows=[]
    geom=(a.data/'frame905.geometry').read_bytes();raw=(a.data/'frame905.raw').read_bytes()
    for mode in ['bad_payload_CRC','bad_status_CRC','old_wire_version','reject_prepare']:
        m=Guard(a.arm,mode);m.packets,_,_=(old_encode if mode=='old_wire_version'else encode)(geom,raw,905)
        m.index=0;m.start_token=0;m.prepared=False;m.spi_calls=0
        if mode=='reject_prepare':
            while m.state_value()!=2:assert m.call('nes_native165_poll',[m.state,m.spi|1,0])==1
            assert m.call('nes_native165_prepare',[m.state,0,m.spi|1,0])==1
        else:assert m.call('nes_native165_poll',[m.state,m.spi|1,0])==0
        assert m.state_value()==5
        assert m.call('nes_native181_pixels',[m.state,0])==0,'tentative raw exposed'
        before=len(m.calls);assert m.call('nes_native165_poll',[m.state,m.spi|1,0])==0 and len(m.calls)==before
        rows.append(dict(case=mode,state=m.state_value(),error=m.u.mem_read(m.state+m.layout['nes_native165']['error'],1)[0],SPI_calls=len(m.calls),tentative_pixels_hidden=True,no_retry=True))
    report=dict(passed=True,firmware_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'),scope=__doc__,rows=rows)
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
