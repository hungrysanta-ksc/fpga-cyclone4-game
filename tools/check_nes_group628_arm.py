# SPDX-License-Identifier: MIT
"""Exercise the linked encoder's exact masks, bounded-history fallback and abort/reset."""
import argparse
import json
from pathlib import Path
import struct

from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, sha
from check_nes_supply485_arm import ARM


def run(a):
    m=ARM(a.src,'normal')
    m.s=0x20010000
    ptr=0x20018000
    m.setup()
    layout=m.layout['nes_native_sink165']
    m.put(m.s,'nes_native_sink165','plan',0,4)
    packets=[]
    def enqueue(u,pc,size,user):
        packets.append(bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2))))
        u.reg_write(UC_ARM_REG_R0,0 if reject else 1)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    pc=m.syms['nes_window184_enqueue']
    m.u.hook_add(UC_HOOK_CODE,enqueue,begin=pc,end=pc)
    reject=False
    group=b'\x01\x02\x03\x04'
    runs=(b'\xff'+group)*2+b'\x02'+group
    bases=m.s+layout['base628']
    history=m.s+layout['history628']
    results=[]
    def submit(at,data):
        m.u.mem_write(ptr,data)
        return m.call('packet_wire',[m.s,2,2,at,ptr,len(data),0])
    for n in (64,128,192):
        for serial in (3,4,65538,0xfffffffe):
            bank=(serial-1)&1
            m.put(m.s,'nes_native_sink165','serial',serial,4)
            m.u.mem_write(bases+4*bank,struct.pack('<I',serial-2))
            m.u.mem_write(history+880*bank,runs)
            for indices in ([],[0],[n//4-1],list(range(1,n//4,5)),list(range(n//4))):
                b=bytearray(group*(n//4))
                for i in indices:b[4*i]^=i+1
                assert submit(4096-n,bytes(b))
                h=packets[-1]
                if len(indices)==n//4:
                    assert h[0]==2 and h[16:]==b
                else:
                    assert h[0]==9 and int.from_bytes(h[16:20],'little')==serial-2
                    sz=n//32
                    mask=int.from_bytes(h[24:24+sz],'little')
                    assert mask==sum(1<<i for i in indices)
                    assert h[24+sz:]==b''.join(b[4*i:4*i+4] for i in indices)
                    words=struct.unpack('<'+'H'*(n//2),b)
                    assert struct.unpack_from('<HH',h,20)==(sum(words)%65536,sum(w*(len(words)-j) for j,w in enumerate(words))%65536)
                results.append(h[0])
    bank=(serial-1)&1
    for content in (bytes(880),(b'\x01'+group)*176):
        m.u.mem_write(history+880*bank,content)
        assert submit(4032,group*16) and packets[-1][0]==2
    m.u.mem_write(bases+4*bank,struct.pack('<I',serial-3))
    m.u.mem_write(history+880*bank,runs)
    assert submit(2048,group*16) and packets[-1][0]==2
    m.u.mem_write(bases+4*bank,struct.pack('<I',serial-2))
    assert submit(2048,group*16) and packets[-1][0]==9
    reject=True
    assert not submit(2112,group*16) and packets[-1][0]==9
    assert m.u.mem_read(bases,8)==bytes(8) and m.get(m.s,'nes_native_sink165','error')
    m.u.mem_write(bases,b'\xff'*8)
    m.call('nes_sink165_reset',[m.s,m.syms['nes_window184_barrier']|1,m.w])
    assert m.u.mem_read(bases,8)==bytes(8)
    a.out.write_text(json.dumps(dict(vectors=len(results),delta=results.count(9),literal=results.count(2),
        invalid_run_fallback=2,stale_fallback=True,partial_abort_and_reset=True,firmware=sha(a.src/'obj-nes-100/firmware.stm')),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    run(p.parse_args())
