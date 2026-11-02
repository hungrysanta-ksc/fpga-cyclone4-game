# SPDX-License-Identifier: MIT
"""Exercise a delayed, actual bulk retirement at the linked map packet entry."""
import argparse
import json
from pathlib import Path
from test_nes_overlap508_arm import ARM, Mixed, sha, crc


class SlowTile(Mixed):
    def __init__(self):
        super().__init__()
        self.before=[]

    def exchange(self,tx,clock):
        self.advance(clock)
        if tx[0]==0xe1:
            self.before.append((tx[1],tx[2],self.sent-self.retired,any(b[0]==7 for _,b in self.pending)))
        result=super().exchange(tx,clock)
        if tx[0]==0xe8 and self.mode=='changed_descriptor':
            r=bytearray(result)
            assert r[6]
            r[8]^=16  # Same token and valid response CRC, different descriptor.
            r[19]=crc(r[1:19],8,7,0)
            return bytes(r)
        if tx[0]==0xe1:
            self.pending[-1]=(clock+90000,self.pending[-1][1])
        return result


def case(src,*,prefix=0,section=2,patched=True,fault=None):
    m=ARM(src,'normal')
    e=m.endpoint=SlowTile()
    m.setup()
    payload=0x20002300
    m.u.mem_write(payload,bytes(range(192)))
    def send(k):return m.call('packet_wire',[m.s,2,k,0,payload,192,0])
    for _ in range(prefix):assert send(3)
    for key,val,size in [('started',1,1),('ending',1,1),('generation',907,2),('sent',1,2)]:
        m.put(m.p,'nes_plan200',key,val,size)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    e.jobs=[(1,0,32,1)];e.accepted=1;e.end=True
    assert send(section)
    assert [r[0] for r in e.before]==[2]*prefix+[7,2]
    early=e.before[-1][3]
    assert early==(patched and prefix<2 and section==2)
    if early:
        assert m.get(m.p,'nes_plan200','bulk_pending') and e.before[-1][2]<=2
    if fault:
        e.mode=fault
    ok=m.call('nes_plan200_progress',[m.p,1])
    assert bool(ok)==(not fault)
    if ok:assert m.call('nes_window184_drain',[m.w,0x20002400]) and e.sent==e.retired
    else:
        before=len(e.calls)
        assert not send(section) and before==len(e.calls)
    assert not m.get(m.s,'nes_native_sink165','displayed') and not e.rearmed
    return dict(prefix=prefix,section=section,early=early,mode=fault or 'normal',sent=e.sent,retired=e.retired)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('arm','base','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    rows=[case(a.base,patched=False),*(case(a.arm,prefix=k) for k in (0,1,2)),case(a.arm,section=3),
          case(a.arm,fault='STOP_after_bulk'),case(a.arm,fault='changed_descriptor'),case(a.arm,fault='bad_accepted')]
    a.out.write_text(json.dumps(dict(sha=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
