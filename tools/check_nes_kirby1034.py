"""Check the physical header layout, ARM sampler cadence and final-link return guards."""
import json
import re
import struct

from check_nes_frame862_arm import TimedProbe, timer_cases, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_HOOK_CODE
from check_nes_kirby1024_journal import replay
from check_nes_menu533 import check
from prepare_nes_kirby1034 import PROBES
from read_nes_kirby1034 import CAPACITY, HEADER, INGRESS, OFFSET, ROW, SIZE, decode


def layout(h):
    def read(header=h, gen=1561, last=0x2100, age=0, duration=0x2800):
        data=bytearray(SIZE)
        HEADER.pack_into(data,0,0x9001,1034,0,1,0,0,ROW.size,CAPACITY)
        desc=struct.pack('<BBHHHI',1,1,192,320,1561,3184)
        ROW.pack_into(data,HEADER.size,5900,1561,661,1800,10,5,16,2,7,1,header,desc)
        INGRESS.pack_into(data,OFFSET,0xfffff000,(duration-0x1000)&0xffffffff,
                         (last-0x1000)&0xffffffff,1200,500,age*2**24+1900,gen,17)
        return decode(bytes(data))['rows'][0]
    good=read()
    assert good['E9_accept_ticks']==[13,16,19,22]
    assert [r['tick'] for r in good['bank_returns']]==[16,19,22,27]
    assert good['last_group_start_tick']==22 and good['final_ACK_tick']==30
    assert read(age=127)['first_block_ready_ms'][0] is None
    assert 'unresolved' in read(gen=1560) and 'unresolved' in read(last=0x3000)
    for i in (1,2,12,30,31):
        bad=bytearray(h);bad[i]^=1
        assert 'unresolved' in read(bad)
    bad=bytearray(h); bad[21]+=16
    overflow=read(bad)
    assert not overflow['E9_list_complete'] and overflow['bank_returns']==good['bank_returns']
    return good


def sampling(src,header,edition=1034):
    q=TimedProbe(src)
    q.call('nes_budget210_reset',[])
    calls=[]
    def reply(cpu,pc,size,data):
        assert cpu.reg_read(UC_ARM_REG_R3)==32
        calls.append(tick)
        h=bytearray(header);h[2:4]=struct.pack('<H',tick);h[5]=0
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),bytes(h))
        q.ret(cpu,1)
    pc=q.syms['nes_native165_bulk']
    q.u.hook_add(UC_HOOK_CODE,reply,None,begin=pc,end=pc)
    expected=list(range(5500,5750,10))+list(range(5750,6000,5))
    for tick in (2999,3000,5499,*sorted(expected+[v+2 for v in expected]),6000):
        q.put(q.video,'nes_native_video165','generation',tick,2)
        q.call('input900',[tick])
        q.call('e0900',[tick,0])
        q.call('nes_budget210_frame',[tick])
        q.call('nes_budget210_display',[tick,q.video])
        q.call('finish_header950',[])
    data=bytes(q.u.mem_read(q.data['ptrcache'],SIZE))
    assert HEADER.unpack_from(data)==(0x9001,edition,0,75,0,0,ROW.size,CAPACITY)
    assert calls==expected
    for i,tick in enumerate(calls):
        row=ROW.unpack_from(data,HEADER.size+i*ROW.size)
        assert row[:2]==(tick,tick) and row[8]&4
    return len(calls)


if __name__=='__main__':
    work=PROBES/'nes-kirby1034'
    src=work/'link/src'
    text=(work/'observer.log').read_text()
    assert 'PASS1034' in text
    h=bytes.fromhex(re.search(r'^# HEADER1034 ([a-f0-9]{64})$',text,re.M)[1])
    report=dict(checked_header=layout(h),sampled_windows=sampling(src,h),
                timer=timer_cases(src),menu=check(src,'1034'),journal=replay(work,1034,[]))
    assert report['timer']['passed'] and report['menu']['rows']['normal']['released']
    (work/'proof/qualification.json').write_text(json.dumps(report,indent=2)+'\n')
