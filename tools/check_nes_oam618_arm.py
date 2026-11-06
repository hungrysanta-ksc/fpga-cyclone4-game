# SPDX-License-Identifier: MIT
"""Check the actual OAM yield and STOP path after the checked map/palette boundary."""
import argparse
import json
from pathlib import Path

from check_nes_map527 import ARM,sha
from check_nes_game478 import UC_HOOK_CODE
from check_nes_supply485_arm import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR


def check(src,rows,stop_at):
    m=ARM(src,'normal')
    m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    # Already sent the map. Isolate the interval between palette and OAM.
    m.put(m.s,'nes_native_sink165','map_next',64,1)
    for field,value,n in [('serial',1,4),('generation',907,2),('prepared',1,1),('open',1,1),
                           ('map_upload',((1<<rows)-1)<<32,8)]:
        m.put(m.resident,'nes_resident211',field,value,n)
    for field,value,n in [('valid',1,1),('generation',907,2),('bg_count',1,2),
                           ('hdma_size',3,2),('display_mask',0x1e,1)]:
        m.put(m.video,'nes_native_video165',field,value,n)
    spans=[]
    pauses=[]
    def span(u,pc,size,user):
        section=u.reg_read(UC_ARM_REG_R1)
        spans.append(section)
        # Stand in for an already accepted palette and stop the normal control
        # at its first OAM span. The admission comparison and delay are real.
        u.reg_write(UC_ARM_REG_R0,int(section==3))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def pause(u,pc,size,user):
        # Credit/drain progress may also call this helper before the palette.
        # Count only the explicit quiet calls between palette and OAM.
        if spans!=[3] or u.reg_read(UC_ARM_REG_R2)!=0 or u.reg_read(UC_ARM_REG_R3)!=0:return
        pauses.append(pc)
        if len(pauses)==stop_at:
            m.endpoint.mode='STOP_after_E9';m.endpoint.accepted=1
    for name,hook in [('span',span),('nes_cost474_pause',pause)]:
        pc=m.syms[name];m.u.hook_add(UC_HOOK_CODE,hook,begin=pc,end=pc)
    assert not m.call('nes_sink212_seal',[m.s,m.video,m.resident])
    assert len(pauses)==(0 if rows<=18 else stop_at or 2)
    assert spans==([3] if stop_at else [3,4])
    if stop_at:assert m.get(m.s,'nes_native_sink165','error')==5
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(rows=rows,STOP_at=stop_at,pauses=len(pauses),sections=spans)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    cases=[check(a.src,n,k) for n,k in ((18,0),(19,0),(19,1),(19,2))]
    a.out.write_text(json.dumps(dict(ARM=sha(a.src/'obj-nes-100/firmware.stm'),cases=cases),indent=2)+'\n')
