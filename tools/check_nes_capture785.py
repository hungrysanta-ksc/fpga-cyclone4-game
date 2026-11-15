# SPDX-License-Identifier: MIT
"""Exercise linked PREPARE, COMMIT and validated status reuse at token wrap."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_idle676 import Receiver
from check_nes_game478 import crc, sha, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_LR


class Commit(Receiver):
    def hook(self,u,at,size,user):
        if at!=self.spi:
            return super().hook(u,at,size,user)
        tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R3)))
        op=tx[0]
        self.ops.append(op)
        if op in (0xd0,0xd2,0xd3):
            assert tx[5]==(255^tx[4]) and tx[6]==crc(tx[:6],8,7,0) and tx[7]==165
        rx=self.status()
        if op==0xd3:
            assert tx[2:5]==bytes([0,9,1]) and self.state_value()==2
            self.prepared=True
        elif op==0xd1:
            assert self.prepared and self.state_value()==3 and self.index==0
            packet=self.packets[0]
            rx=b'\0'+packet+crc(packet,16,0x1021,65535).to_bytes(2,'big')
        elif op==0xd2:
            assert tx[2:4]==bytes([255,255])
            self.index+=1
        else:assert op==0xd0
        stopped=self.case=="stop_commit" and op==0xd1
        u.mem_write(u.reg_read(UC_ARM_REG_R2),rx)
        u.reg_write(UC_ARM_REG_R0,int(not stopped));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))


def exercise(src,case,limited=False):
    m=Commit(src,case)
    m.prepared=False
    m.start_token=65535
    m.packets=[struct.pack(">HHQ",0xe003,9,0)]
    for key,v,n in (("state",2,1),("generation",9,2),("token_valid",1,1),("next_token",65535,2)):
        m.put(m.state,"nes_native165",key,v,n)
    ready=bytearray(m.status())
    if case=="bad_token":ready[4]^=1;ready[7]=crc(ready[1:7],8,7,0)
    if case=="bad_crc":ready[7]^=1
    m.u.mem_write(m.state+m.layout["nes_native165"]["status183"],bytes(ready))
    m.put(m.state,"nes_native165","ready183",int(case!="uncached"),1)
    ok=m.call("nes_native165_prepare",[m.state,1,m.spi|1,0])
    if case in ("bad_token","bad_crc"):
        assert not ok and not m.ops and m.state_value()==5
    else:
        assert ok and m.state_value()==3
        prefix=([0xd0] if case=="uncached" else [])+[0xd3,0xd0]
        assert m.ops==prefix
        ok=m.call("nes_native165_poll",[m.state,m.spi|1,0])
        assert bool(ok)==(case!="stop_commit")
        if limited and case=="uncached":prefix+=[0xd0]
        if case=="stop_commit":assert m.ops==prefix+[0xd1] and m.state_value()==5
        else:assert m.ops==prefix+[0xd1,0xd2,0xd0] and m.state_value()==4 and m.get(m.state,"nes_native165","next_token",2)==0
    return dict(case=case,ops=m.ops,state=m.state_value())


def retirement(src, case, complete=None):
    from check_nes_handoff678 import Handoff
    m=Handoff(src,"normal")
    m.setup()
    for k,v,n in (("started",1,1),("finished",int(case!="no_finish"),1),("generation",907,2),("sent",4,2)):
        m.put(m.p,"nes_plan200",k,v,n)
    for k,v,n in (("state",0,1),("displayed",int(case!="no_ACK"),1),("last_generation",907,2)):
        m.put(m.s,"nes_native_sink165",k,v,n)
    ops=[]
    def exchange(tx,clock):
        op=tx[0]
        ops.append(op)
        if op==0xea:
            assert tx[1:5]==struct.pack("<H",907)+bytes((0,4)) and tx[5]==crc(tx[:5],8,7,0) and tx[6]==165
            if case=="stop_after_EA":
                m.endpoint.mode="STOP_after_bulk";m.endpoint.bulk=1
            return bytes(7)
        assert op==0xe8
        rx=bytearray(20);rx[1:4]=bytes((0xd7,4,1))
        if complete is False and len(ops)==1:
            rx[3],rx[5]=2,4
        if case=="count":rx[5]=1
        if case=="descriptor":rx[6]=1
        if case=="fault":rx[3]|=128
        if case=="busy" and len(ops)==(3 if complete is False else 2):rx[3]=6;rx[5]=4
        rx[19]=crc(rx[1:19],8,7,0)^(case=="crc")
        return bytes(rx)
    m.endpoint.exchange=exchange
    ok=(m.call("nes_plan200_retire",[m.p]) if complete is None else
        m.call("nes_plan200_handoff790",[m.p,int(complete)]))
    assert bool(ok)==(case in ("normal","busy"))
    if case in ("no_finish","no_ACK"):
        expected=[]
    elif complete is False and case in ("count","descriptor","fault","crc"):
        expected=[0xe8]
    else:
        expected=[0xe8] if complete is False else []
        expected.append(0xea)
        if case!="stop_after_EA":
            expected.extend([0xe8,0xe8] if case=="busy" else [0xe8])
    assert ops==expected,(case,complete,ops,expected)
    assert bool(m.get(m.p,"nes_plan200","started"))!=bool(ok)
    return dict(case=case,passed=bool(ok),ops=ops)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("src",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--limited",action="store_true")
    p.add_argument("--retire",action="store_true")
    p.add_argument("--retire-only",action="store_true")
    a=p.parse_args()
    cases=[] if a.retire_only else [exercise(a.src,c,a.limited) for c in ("cached","uncached","bad_crc","bad_token","stop_commit")]
    if a.retire or a.retire_only:
        cases.extend(retirement(a.src,c) for c in ("normal","busy","no_finish","no_ACK","stop_after_EA","count","descriptor","fault","crc"))
    a.out.write_text(json.dumps(dict(firmware=sha(a.src/"obj-nes-100/firmware.stm"),cases=cases),indent=2)+"\n")
