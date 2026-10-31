# SPDX-License-Identifier: MIT
"""Exercise the linked M4 mask history with alternating banks, stale ACKs, STOP and epoch change."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Machine, sha

def check(a):
    m=Machine(a.arm,bytes(128))
    s=m.resident
    mask=s+m.layout["nes_resident211"]["map_groups"]
    changed=s+m.layout["nes_resident211"]["size"]+16
    cold=b"\xff"*64
    empty=bytes(64)
    x=b"\x81"+empty[1:]
    y=empty[:16]+b"\x08"+empty[17:]
    xy=bytes(v|w for v,w in zip(x,y))
    def history(a,b):
        assert bytes(m.u.mem_read(mask,128))==a+b
    def begin(epoch,gen):
        assert m.call("nes_resident211_begin",[s,epoch,1,gen,m.writer|1,0])==1
    def prepare(bits):
        m.u.mem_write(changed,bits)
        assert m.call("nes_resident211_prepare",[s,changed])==1
    def ack(serial,gen,bank,shown=True):
        return bool(m.call("nes_resident211_commit",[s,serial,gen,bank,int(shown)]))
    def reset():
        m.call("nes_resident211_reset",[s]);history(cold,cold)
    def warm():
        reset()
        begin(1,905);prepare(empty);history(cold,cold);assert ack(1,905,0);history(empty,cold)
        begin(1,906);prepare(x);history(x,cold);assert ack(2,906,1);history(x,empty)
        begin(1,907);prepare(y);history(xy,y)
    events=[]
    for name,(ser,gen,bank,shown) in {
        "stale_serial":(2,907,0,True),"wrong_generation":(3,906,0,True),
        "wrong_bank":(3,907,1,True),"without_display":(3,907,0,False)}.items():
        warm();assert not ack(ser,gen,bank,shown);history(cold,cold)
        assert not ack(3,907,0);events.append(name)
    warm();m.call("nes_resident211_abort",[s]);history(cold,cold)
    assert not ack(3,907,0);events.append("STOP_late_ACK")
    warm();assert ack(3,907,0);history(empty,y);begin(2,908);history(cold,cold)
    prepare(empty);history(cold,cold);assert ack(4,908,1);history(cold,empty);events.append("new_epoch")
    a.out.write_text(json.dumps(dict(passed=True,cases=events,firmware_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'),
                                     resident_B=m.layout['nes_resident211']['size'],video_B=m.layout['nes_native_video165']['size']),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','out'):p.add_argument('--'+name,type=Path,required=True)
    check(p.parse_args())
