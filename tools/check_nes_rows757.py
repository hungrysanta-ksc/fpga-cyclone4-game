# SPDX-License-Identifier: MIT
"""Run the linked publication helper at sparse, duplicate, cancellation and priority boundaries."""
import argparse
import json
from pathlib import Path
from check_nes_credit752 import verify
from check_nes_supply485_arm import ARM
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_LR,UC_ARM_REG_PC


def guards(src,mode):
    proof={}
    machine=ARM(src,'normal')
    machine.setup()
    sink='nes_native_sink165'
    machine.put(machine.s,sink,'plan',machine.p,4)
    packets=[]
    ready={'nes_plan527_map_credit':True,'nes_window532_room':True}
    failed=None
    def hook(name):
        def capture(u,pc,size,user):
            if name in ready:
                u.mem_write(u.reg_read(UC_ARM_REG_R1),bytes([ready[name]]))
            else:
                at=u.reg_read(UC_ARM_REG_R1)
                data=bytes(u.mem_read(at,208))
                assert data[:2]==bytes([2,2]) and int.from_bytes(data[12:14],'little')==192
                offset=int.from_bytes(data[10:12],'little')
                assert data[16:]==tilemap[offset:offset+192]
                packets.append(offset)
            u.reg_write(UC_ARM_REG_R0,int(name!=failed))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        address=machine.syms[name]
        machine.u.hook_add(UC_HOOK_CODE,capture,begin=address,end=address)
    for name in (*ready,'nes_window184_enqueue'):hook(name)
    tilemap=bytes(range(256))*16
    machine.u.mem_write(machine.video+machine.layout['nes_native_video165']['map'],tilemap)
    # uint64_t pending occupies r2/r3, with 'finished' on the AAPCS stack.
    def offer(limit,mask=0xffffff):
        return machine.call('nes_map757_offer',[machine.s,machine.video,0,mask,limit])
    first=6 if mode=='tail' else 0
    limit_two=first+2
    assert offer(first) and not packets
    for flag in ready:
        ready[flag]=False
        assert offer(limit_two) and not packets
        ready[flag]=True;failed=flag
        assert not offer(limit_two) and not packets
        failed=None
    assert offer(first+1,6<<(first*3)) and not packets
    failed='nes_window184_enqueue'
    assert not offer(first+1) and machine.get(machine.s,sink,'right757')==0
    machine.setup();machine.put(machine.s,sink,'plan',machine.p,4)
    failed=None;packets.clear()
    assert offer(limit_two) and len(packets)==(1 if mode=='row' else 2)
    for limit in range(first+1,9):
        count=len(packets)
        assert offer(limit)
        assert all(offset+192<=2048+192*limit for offset in packets[count:])
    assert packets==list(range(2048+192*first,3584,192)) and machine.get(machine.s,sink,'right757')==((255<<first)&255)
    assert offer(8) and len(packets)==8-first
    proof['range_guards']=dict(failed_enqueue_unpublished=True,blocked_room_and_tile=True,
        sparse_fallback=True,duplicate_free=True,offsets=packets)
    proof.update(verify(src,'mapobj'))
    return proof

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path);p.add_argument('mode',choices=('row','pair','page','tail'));p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(guards(a.src,a.mode),indent=2)+'\n',encoding='utf8')
