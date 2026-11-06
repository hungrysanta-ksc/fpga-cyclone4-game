# SPDX-License-Identifier: MIT
"""Run linked ARM ordering and STOP guards on both sides of the 19-row boundary."""
import argparse
import json
from pathlib import Path

from check_nes_oam618_arm import ARM, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_PC, sha
from check_nes_game478 import UC_ARM_REG_SP


def exercise(src, expected, rows, stop, bg=0, obj=0):
    m = ARM(src, 'normal')
    m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.s,'nes_native_sink165','map_next',64,1)
    m.put(m.s,'nes_native_sink165','bg_next',bg,2)
    m.put(m.s,'nes_native_sink165','obj_next',obj,2)
    for field in ('ending','finished'):
        m.put(m.p,'nes_plan200',field,1,1)
    for field,value,n in [('serial',1,4),('generation',907,2),('prepared',1,1),('open',1,1),('map_upload',((1<<rows)-1)<<32,8)]:
        m.put(m.resident,'nes_resident211',field,value,n)
    for field,value,n in [('valid',1,1),('generation',907,2),('bg_count',1,2),('hdma_size',3,2),('display_mask',30,1)]:
        m.put(m.video,'nes_native_video165',field,value,n)
    stages = []
    calls = []
    def enter(stage):
        stages.append(stage)
        if stage==stop:
            m.endpoint.mode='STOP_after_E9'
            m.endpoint.accepted=1
            calls.append(len(m.endpoint.calls))

    def span(u,pc,size,user):
        stage = {3:'palette',4:'OAM'}[u.reg_read(UC_ARM_REG_R1)]
        if stage=='palette':
            off=u.reg_read(UC_ARM_REG_R2)
            length=int.from_bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP),4),'little')
            assert u.reg_read(UC_ARM_REG_R3)==m.video+m.layout['nes_native_video165']['cgram']+off
            if 'palette_tail' in expected:
                assert (off,length) in ((0,128),(128,384))
                if off:stage='palette_tail'
            else:
                assert (off,length)==(0,512)
        enter(stage)
        if stage!=stop:
            # Isolate the boundary after an accepted palette; stop the normal case at OAM.
            u.reg_write(UC_ARM_REG_R0, int(stage!='OAM'))
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def pause(u,pc,size,user):
        ret = u.reg_read(UC_ARM_REG_LR) & ~1
        if max(addr for addr in m.syms.values() if addr<=ret-2)==m.syms['nes_sink212_seal']:
            enter('pause2' if 'pause1' in stages else 'pause1')

    for name, hook in [('span',span),('nes_window184_drain',lambda *args: enter('drain')),('nes_cost474_pause',pause)]:
        pc=m.syms[name]
        m.u.hook_add(UC_HOOK_CODE, hook, begin=pc, end=pc)
    assert not m.call('nes_sink212_seal',[m.s,m.video,m.resident])
    assert stages==(expected[:expected.index(stop)+1] if stop else expected)
    assert not m.get(m.s,'nes_native_sink165','displayed')
    if stop:
        assert calls==[len(m.endpoint.calls)] and m.get(m.s,'nes_native_sink165','error')==5
    return dict(rows=rows,bg_units=bg,obj_units=obj,stop=stop,stages=stages)


def split_payload(src):
    # Capture the bytes actually handed to the queue by the two linked spans.
    m=ARM(src,'normal')
    m.setup()
    buf=m.video+m.layout['nes_native_video165']['cgram']
    slot=m.guard485-8
    m.put(m.s,'nes_native_sink165','enqueue',slot|1,4)
    packets=[]
    def queue(u,pc,size,user):
        packets.append(bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2))))
        u.reg_write(UC_ARM_REG_R0,1)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    m.u.hook_add(UC_HOOK_CODE,queue,begin=slot,end=slot)
    literal=bytes((i*37)%251 for i in range(512))
    vectors=[literal,b'\x35\xa2'*256,literal[:33]+b'\x00'*214+literal[247:]]
    for palette in vectors:
        packets.clear()
        m.u.mem_write(buf,palette)
        for off,n in ((0,128),(128,384)):
            assert m.call('span',[m.s,3,off,buf+off,n])
        received=bytearray()
        for b in packets:
            assert b[1]==3 and int.from_bytes(b[10:12],'little')==len(received)
            n=int.from_bytes(b[12:14],'little')
            expanded=int.from_bytes(b[14:16],'little')
            data=b[16:]
            assert n==len(data)
            if b[0] in (4,5):
                assert n==2 and expanded%2==0
                data*=expanded//2
            else:
                assert b[0]==2 and expanded==0
            received.extend(data)
        assert bytes(received)==palette
    return len(vectors)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--split',action='store_true')
    p.add_argument('--credit-only',action='store_true')
    a=p.parse_args()
    orders={'after-pack':['drain','palette','pause1','pause2','OAM'],
            'after-pause':['drain','pause1','pause2','palette','OAM'],
            'advance':['palette','drain','pause1','pause2','OAM']}
    if a.split:
        orders={'split':['drain','palette','pause1','pause2','palette_tail','OAM']}
    if a.credit_only:
        orders={'credit-only':orders['after-pack']}
    result={}
    for policy, order in orders.items():
        src=a.build/policy/'src'
        cases=[exercise(src,[stage for stage in order if stage in ('palette','palette_tail','OAM')],18,None)]
        cases.extend(exercise(src,order,19,s) for s in [None,*order])
        result[policy]=dict(arm=sha(src/'obj-nes-100/firmware.stm'),cases=cases)
        if policy=='split':
            result[policy]['palette_roundtrips']=split_payload(src)
        if policy=='credit-only':
            for bg,obj in ((0,1),(4,0),(1,1),(4,1),(5,1)):
                active=order if not obj or bg not in range(1,5) else order[1:]
                cases.append(exercise(src,active,19,None,bg,obj))
                if (bg,obj)==(4,1):
                    cases.extend(exercise(src,active,19,stage,bg,obj) for stage in active)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
