# SPDX-License-Identifier: MIT
"""Check linked ARM mask traversal, packet contents and restart after a failed enqueue."""
import argparse
import json
from pathlib import Path
from random import Random

from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, sha
from check_nes_supply485_arm import ARM


def check(src):
    m=ARM(src,'normal')
    image=Random(626).randbytes(4096)
    m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],image)
    sent=[]
    def capture(u,at,size,user):
        packet=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)))
        assert packet[:2]==b'\x02\x02'
        offset=int.from_bytes(packet[10:12],'little')
        n=int.from_bytes(packet[12:14],'little')
        assert n in (64,128,192) and offset%64==0 and len(packet)==16+n
        assert packet[16:]==image[offset:offset+n]
        sent.append((offset//64,n//64))
        u.reg_write(UC_ARM_REG_R0,int(not reject))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    pc=m.syms['nes_window184_enqueue']
    m.u.hook_add(UC_HOOK_CODE,capture,begin=pc,end=pc)
    rng=Random(626)
    masks=[0,2**64-1]+[x<<29 for x in range(512)]+[rng.getrandbits(64) for _ in range(128)]
    for j,mask in enumerate(masks):
        m.setup()
        sent.clear()
        reject=False
        def invoke(early):
            return m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,int(early)])
        for _ in range(j%8):
            assert invoke(True)
        assert invoke(False)
        rows=sorted(row for start,n in sent for row in range(start,start+n))
        assert rows==[i for i in range(64) if mask>>i&1]
        if mask==2**64-1:
            # Full cold runs cross the page boundary and retain their original grouping.
            assert sent[:2]==[(0,3),(3,3)]
    mask=0x3f<<32
    m.setup()
    sent.clear()
    reject=True
    assert not invoke(True) and sent==[(35,3)] and m.get(m.s,'nes_native_sink165','map_next')==0
    m.setup()
    reject=False
    sent.clear()
    assert invoke(True) and invoke(False) and sent==[(35,3),(32,3)]
    restarted=sent.copy()
    m.setup()
    m.put(m.s,'nes_native_sink165','map_next',128,1)
    sent.clear()
    assert invoke(False) and sent==restarted
    return dict(masks=len(masks),rejected_cursor=0,restart=restarted,no_early_credit=sent,
                firmware=sha(src/'obj-nes-100/firmware.stm'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.src),indent=2)+'\n')
