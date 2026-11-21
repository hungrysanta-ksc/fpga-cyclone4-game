"""Exercise the final D3 status and subsequent COMMIT on the linked Cortex-M4."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from check_nes_game478 import Machine, crc
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3


class Receiver(Machine):
    def hook(self,u,at,size,user):
        if at!=self.spi:
            return super().hook(u,at,size,user)
        n=u.reg_read(UC_ARM_REG_R3)
        tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n))
        op=tx[0]
        self.bus.append(op)
        if op in (0xd0,0xd2,0xd3):
            assert tx[-2]==crc(tx[:6],8,7,0) and tx[-1]==0xa5
        if op==0xd1:
            if self.end_head:
                packet=struct.pack('>HHQ',0xe001,self.gen,0)
            elif self.case=='overflow':
                packet=struct.pack('>HHQ',0xe002,self.gen,6)
            else:
                packet=struct.pack('>HHQ',0xe003,self.gen+int(self.case=='generation'),0)
            rx=b'\0'+packet+(crc(packet,16,0x1021,65535)^int(self.case=='data_crc')).to_bytes(2,'big')
        else:
            ready=self.end_head or (self.prepared and not self.popped)
            if self.case=='delayed' and self.bus[-2:]==[0xd3,0xd0]:
                ready=False
            token=(self.token+int(self.popped and self.case!='pop'))&65535
            if ready and self.case=='token':
                token^=1
            end_flag=0 if (self.case=='end_late' and not self.prepared and
                           self.bus[-2:]==[0xd2,0xd0]) else 2
            rx=bytearray(struct.pack('>BBBHH',0,0xd6,end_flag|int(ready),token,12 if ready else 0))
            rx.append(crc(rx[1:],8,7,0)^int(self.case=='status_crc' and self.prepared))
            if op==0xd3:
                assert tx[4]==int(self.case not in ('reject','overflow','bad_abort'))
                self.prepared=True
            elif op==0xd2:
                assert int.from_bytes(tx[2:4],'big')==self.token
                if self.end_head:
                    self.end_head=False
                    self.token=(self.token+1)&65535
                else:
                    self.popped=True
        assert len(rx)==n
        u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(rx))
        u.reg_write(UC_ARM_REG_R0,int(not (self.case=='stop' and op==0xd1)))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))


def run(src):
    m=Receiver(src,bytes(128))
    fields=m.layout['nes_native165']
    result={}
    for case in ('ok','end_sequence','end_late','end_crc','delayed','status_crc','cached_crc',
                 'data_crc','token','generation','pop','stop','reject','reset','overflow','bad_abort'):
        m.call('nes_native165_reset',[m.state])
        m.bus=[];m.prepared=False;m.popped=False;m.case=case;m.gen=934;m.token=65535
        m.end_head=case.startswith('end_')
        for field,value,width in [('state',1 if m.end_head else 2,1),('generation',m.gen,2),
                                  ('next_token',m.token,2),('token_valid',1,1),('next_kind',7,1)]:
            m.u.mem_write(m.state+fields[field],value.to_bytes(width,'little'))
        corrupt_end=False
        if m.end_head:
            assert m.call('nes_native165_poll',[m.state,m.spi|1,0]) and m.state_value()==2
            corrupt_end=case=='end_crc' and bool(m.u.mem_read(m.state+fields['ready183'],1)[0])
            if corrupt_end:
                addr=m.state+fields['status183']+7
                m.u.mem_write(addr,bytes([m.u.mem_read(addr,1)[0]^1]))
        if case in ('overflow','bad_abort'):
            m.u.mem_write(m.state+fields['counts'],struct.pack('<6H',0,0,33,0,0,32))
            m.u.mem_write(m.state+fields['objects'],struct.pack('<Q',1<<38)*33)
            m.u.mem_write(m.state+fields['raster'],struct.pack('<Q',1<<40))
        ok=m.call('nes_native165_prepare',[m.state,int(case!='reject'),m.spi|1,0])
        assert ok==int(case!='status_crc' and not corrupt_end),case
        if corrupt_end:
            assert 0xd3 not in m.bus
        if case=='cached_crc':
            assert m.u.mem_read(m.state+fields['ready183'],1)==b'\1'
            addr=m.state+fields['status183']+7
            m.u.mem_write(addr,bytes([m.u.mem_read(addr,1)[0]^1]))
        if case=='reset':
            m.call('nes_native165_reset',[m.state])
            assert m.state_value()==0 and m.u.mem_read(m.state+fields['ready183'],1)==b'\0'
        elif ok:
            m.call('nes_native165_poll',[m.state,m.spi|1,0])
        normal=case in ('ok','delayed','end_sequence','end_late') or (case=='end_crc' and not corrupt_end)
        if case!='reset':
            expected=4 if normal else 0 if case=='overflow' else 5
            assert m.state_value()==expected,(case,m.state_value(),m.bus)
        if normal:
            assert m.popped and m.bus[-3:]==[0xd1,0xd2,0xd0]
            if not case.startswith('end_'):
                assert m.bus.count(0xd0)==(4 if case=='delayed' else 3)
        if case in ('data_crc','generation','token','stop','cached_crc'):
            assert not m.popped
        result[case]=dict(state=m.state_value(),transactions=[hex(x) for x in m.bus])
    return dict(firmware=hashlib.sha256((src/'obj-nes-100/firmware.stm').read_bytes()).hexdigest(),cases=result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.src),indent=2)+'\n')
