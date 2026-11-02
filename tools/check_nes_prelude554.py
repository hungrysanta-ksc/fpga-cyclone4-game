# SPDX-License-Identifier: MIT
"""Exercise deferred END, SPI faults and tile priority on the linked candidate."""
import argparse
import json
from pathlib import Path
from test_nes_overlap508_arm import ARM,Mixed,crc,sha
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR


class Pending(Mixed):
    def __init__(self):
        super().__init__()
        self.held=True
        self.countdown=0

    def exchange(self,tx,clock):
        result=super().exchange(tx,clock)
        if tx[0]==0xe8 and self.held and not self.end and not result[6]:
            if self.countdown:
                self.countdown-=1
                if not self.countdown:self.held=False
            if self.held:
                result=bytearray(result);result[3]=0
                result[19]=crc(result[1:19],8,7,0)
                if self.mode=='bad_E8_CRC':result[19]^=1
        return bytes(result)


def case(src,mode,cutoff,oam_cutoff=False):
    m=ARM(src,'normal');e=m.endpoint=Pending();m.setup()
    # Model only the empty final map iterator. Real ready/credit/guard,
    # END framing, ordinary packet building and queue checks execute on ARM.
    marker=0x0807ff80
    def empty(u,pc,size,user):
        m.put(m.p,'nes_plan200','quiet_map',0,4)
        u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    m.u.hook_add(UC_HOOK_CODE,empty,begin=marker,end=marker)
    for name,val,size in [('started',1,1),('generation',907,2),('quiet_map',marker|1,4)]:
        m.put(m.p,'nes_plan200',name,val,size)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    assert m.call('nes_plan200_end',[m.p]) and not e.accepted and m.get(m.p,'nes_plan200','count')==1
    buf=0x20002300;m.u.mem_write(buf,bytes(range(32)))
    def send(section):return m.call('packet_wire',[m.s,2,section,0,buf,32,0])
    addr=m.p+m.layout['nes_plan200']['buffer'];sealed=bytes(m.u.mem_read(addr,11))
    assert send(3) and not e.accepted
    if mode=='tile':e.jobs=[(1,0,32,1)]
    if mode in ('bad_E8_CRC','ambiguous_E1'):e.mode=mode
    if mode=='STOP':
        e.mode='STOP_after_E9';e.accepted=1  # activates the existing guard injection
    ok=bool(send(3 if oam_cutoff else 4))
    if mode in ('bad_E8_CRC','ambiguous_E1','STOP'):
        assert not ok
        before=len(e.calls);assert not send(5) and len(e.calls)==before
        assert not any(t.startswith('e9') for t in e.calls)
    else:
        assert ok and bytes(m.u.mem_read(addr,11))==sealed and not e.accepted
        if mode=='tile':
            assert [bytes.fromhex(t)[1] for t in e.calls if t.startswith('e1')]==[2,7,2]
        if mode=='END_first':e.held=False
        elif cutoff:e.countdown=3
        assert send(4 if oam_cutoff else 5)
        if mode=='END_first' or cutoff:
            sent=[bytes.fromhex(t)[0] for t in e.calls if t[:2] in ('e1','e9')]
            assert sent[-2:]==[0xe9,0xe1]
        else:
            assert not e.accepted
            e.countdown=3
        assert m.call('nes_plan200_progress',[m.p,1]) and e.end
        assert [bytes.fromhex(t) for t in e.calls if t.startswith('e9')]==[sealed]
        assert m.call('nes_window184_drain',[m.w,0x20002400]) and e.sent==e.retired
        assert not m.call('nes_plan200_retire',[m.p])  # no final display ACK
    assert not e.rearmed and not m.get(m.s,'nes_native_sink165','displayed')
    return dict(mode=mode,early_ordinary=e.ordinary,bulk=e.bulk,END=e.end)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('arm','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--cutoff',action='store_true')
    p.add_argument('--oam-cutoff',action='store_true')
    a=p.parse_args()
    rows=[case(a.arm,mode,a.cutoff or a.oam_cutoff,a.oam_cutoff) for mode in ('quiet','END_first','tile','STOP','bad_E8_CRC','ambiguous_E1')]
    a.out.write_text(json.dumps(dict(sha=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
