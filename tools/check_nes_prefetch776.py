# SPDX-License-Identifier: MIT
"""Abort a real linked suffix poll between descriptor snapshot and E1 publication."""
import argparse
import json
import struct
from pathlib import Path
from check_nes_supply485_arm import ARM, crc, sha
from check_nes_handoff678 import Handoff


def exercise(src, mode):
    m=ARM(src,'normal')
    m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.s,'nes_native_sink165','plan_wait776',1,1)
    for k,v,n in [('ending',1,1),('started',1,1),('bank_history',2,1),('generation',907,2),('sent',1,2)]:
        m.put(m.p,'nes_plan200',k,v,n)
    m.endpoint.accepted=1
    m.endpoint.jobs=[(1,128,64,160)]
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes((2,2)))
    m.put(m.s,'nes_native_sink165','ack_clock719',(m.instructions-1000000)&0xffffffff,4)
    sent=[]
    exchange=m.endpoint.exchange
    def wire(tx,clock):
        sent.append(tx[0])
        reply=bytearray(exchange(tx,clock))
        if tx[0]==0xe8 and mode=='bad_E8':
            reply[-1]^=1
        if tx[0]==0xe0:
            if mode=='STOP':
                m.endpoint.mode='STOP_after_E9'
            elif mode=='bad_E0':
                reply[-1]^=1
        return bytes(reply)
    m.endpoint.exchange=wire
    assert not m.call('nes_plan200_progress',[m.p,0])
    assert sent==([0xe8] if mode=='bad_E8' else [0xe8,0xe0]),(mode,sent)
    assert m.endpoint.sent==0 and not m.endpoint.rearmed
    return dict(case=mode,opcodes=sent,E1_sent=0)


def immediate(src, case):
    m=Handoff(src,case)
    m.setup()
    p,w,s=m.p,m.w,m.s
    for key,val,n in [('started',1,1),('ending',1,1),('bulk_valid',1,1),('bulk_pending',1,1),
                      ('bulk_until',17,2),('generation',907,2),('poll_limit',4,4)]:
        m.put(p,'nes_plan200',key,val,n)
    m.put(w,'nes_sink_window184','wait',m.callback|1,4)
    for key,val,n in [('ever_sent',1,1),('sent',18,2),('retired',16,2)]:
        m.put(w,'nes_sink_window184',key,val,n)
    last=bytes((9,4))+struct.pack('<HIH',17,1,907)
    m.u.mem_write(w+m.layout['nes_sink_window184']['last'],last)
    prior=bytes((1,1))+struct.pack('<HHHI',64,128,907,160)
    nxt=bytes((1,1))+struct.pack('<HHHI',32,256,907,161)
    m.u.mem_write(p+m.layout['nes_plan200']['bulk'],prior)
    operations=[]
    def exchange(tx,clock):
        op=tx[0]
        operations.append(op)
        r=bytearray(len(tx))
        if op==0xe8:
            second=len(operations)>1
            r[1:3]=bytes((0xd7,4))
            r[6:18]=prior if not second or case=='stuck' else nxt
            if second and case=='mutated':
                r[14:18]=prior[8:12]
            r[19]=crc(r[1:19],8,7,0)^(second and case=='CRC')
        elif op==0xe0:
            r[1:3]=bytes((0xf7,2))
            r[3:7]=struct.pack('>HH',18,18)
            r[7:19]=bytes((0,9))+last[2:]+bytes((0x65,0x9a))
            r[19]=crc(r[1:19],8,7,0)
            if case=='STOP':
                m.endpoint.mode='STOP_after_bulk'
                m.endpoint.bulk=1
        else:
            assert op==0xe1 and case=='normal' and tx[17:21]==nxt[8:12]
        return bytes(r)
    m.endpoint.exchange=exchange
    ok=bool(m.call('nes_plan200_progress',[p,0]))
    assert ok==(case=='normal') and operations.count(0xe1)==int(ok),(case,operations)
    assert operations[:2]==[0xe8,0xe0] and operations.count(0xe8)==dict(normal=2,CRC=2,mutated=2,STOP=1,stuck=4)[case]
    assert not m.get(s,'nes_native_sink165','displayed') and not m.endpoint.rearmed
    return dict(case=case,opcodes=operations,published=ok)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--after-receipt',action='store_true')
    a=p.parse_args()
    if a.after_receipt:
        rows=[immediate(a.src,c) for c in ('normal','STOP','CRC','mutated','stuck')]
    else:
        rows=[exercise(a.src,c) for c in ('bad_E8','bad_E0','STOP')]
    a.out.write_text(json.dumps(dict(firmware=sha(a.src/'obj-nes-100/firmware.stm'),cases=rows),indent=2)+'\n')
