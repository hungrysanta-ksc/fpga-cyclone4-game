# SPDX-License-Identifier: MIT
"""Exercise linked map traversal at the word boundary and real E0/STOP checks."""
import argparse
import json
from pathlib import Path
from random import Random

from analyze_nes_output615 import packets
from check_nes_credit623 import palette_case
from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, sha
from check_nes_supply485_arm import ARM


def check(src,palette):
    machine=ARM(src,'normal')
    image=Random(627).randbytes(4096)
    machine.u.mem_write(machine.video+machine.layout['nes_native_video165']['map'],image)
    sent=[]
    def capture(u,at,size,cookie):
        h=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)))
        offset=int.from_bytes(h[10:12],'little')
        assert h[:2]==b'\x02\x02' and len(h)-16==int.from_bytes(h[12:14],'little')
        assert offset%64==0 and len(h)-16 in (64,128,192) and h[16:]==image[offset:offset+len(h)-16]
        sent.append((offset//64,(len(h)-16)//64))
        u.reg_write(UC_ARM_REG_R0,int(not reject))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    pc=machine.syms['nes_window184_enqueue']
    machine.u.hook_add(UC_HOOK_CODE,capture,begin=pc,end=pc)
    rng=Random(627)
    masks=[0,2**64-1,1<<63]+[v<<29 for v in range(512)]+[rng.getrandbits(64) for _ in range(64)]
    def invoke(early):
        return machine.call('map527',[machine.s,machine.video,mask&0xffffffff,mask>>32,int(early)])
    for j,mask in enumerate(masks):
        machine.setup()
        reject=False
        sent.clear()
        for _ in range(j%5):
            assert invoke(True)
        assert invoke(False)
        expected=[]
        g=0
        while g<64:
            if not mask>>g&1:
                g+=1
                continue
            n=1
            while n<3 and mask>>(g+n)&1:
                n+=1
            expected.append((g,n))
            g+=n
        assert sent==expected
    mask=7<<61
    machine.setup()
    reject=True
    sent.clear()
    assert not invoke(True) and sent==[(61,3)] and machine.get(machine.s,'nes_native_sink165','map_next')==0
    checks=[palette_case(src,palette,4,v) for v in ('normal','bad_crc','bad_count','wrong_identity','STOP_pending','STOP_empty')]
    return dict(masks=len(masks),failed_cursor=0,credit=checks,firmware=sha(src/'obj-nes-100/firmware.stm'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('src','trace','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    pal=bytearray()
    for h,_,_ in packets(a.trace)[957]:
        if h[1]==3:
            assert int.from_bytes(h[10:12],'little')==len(pal)
            pal.extend(h[16:] if h[0]==2 else h[16:]*(int.from_bytes(h[14:16],'little')//2))
    assert len(pal)==512
    a.out.write_text(json.dumps(check(a.src,pal),indent=2)+'\n')
