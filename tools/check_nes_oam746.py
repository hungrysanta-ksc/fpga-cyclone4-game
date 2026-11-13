# SPDX-License-Identifier: MIT
"""Price and test a live ARM staging job against the actual cumulative credit checker."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_handoff678 import Handoff, crc, sha


def check(src, split, case):
    m=Handoff(src,'normal')
    m.setup()
    kind='nes_sink_window184'
    job,source=0x20014500,0x20014600
    raw=bytes((37*i+2)&255 for i in range(112))
    serial=0xfedcba98
    empty=bytes([0xad])*116
    m.u.mem_write(job,empty+struct.pack('<IIB',source,serial,0))
    m.u.mem_write(source,raw)
    for k,v,n in [('sent',0,2),('retired',65535,2),('ever_sent',1,1),('wait',m.callback|1,4),('pending_oam',job,4),('poll_limit',4,4)]:
        m.put(m.w,kind,k,v,n)
    last=bytes((2,1 if case=='tile' else 2))+struct.pack('<HIH',1,4,957)
    m.u.mem_write(m.w+m.layout[kind]['last'],last)
    snapshots=[]
    def exchange(tx,clock):
        assert tx==bytes([0xe0])+bytes(19)
        snapshots.append(bytes(m.u.mem_read(job,116)))
        stale=case=='bound' or (case!='ready' and len(snapshots)<3)
        rx=bytearray(20)
        rx[1:3]=bytes((0xf7,3 if stale else 2))
        rx[3:7]=struct.pack('>HH',0,65535 if stale else 0)
        rx[7:19]=bytes((0,2))+last[2:]+bytes((0x65,0x9a))
        if case=='identity' and not stale:rx[9]^=1
        rx[19]=crc(rx[1:19],8,7,0)^(case=='CRC')
        if case=='STOP':m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
        return bytes(rx)
    m.endpoint.exchange=exchange
    ok=m.call('nes_window184_through',[m.w,m.q,0])
    wanted=raw+struct.pack('<I',serial)
    assert snapshots[0]==empty
    assert bool(ok)==(case in ('pending','ready','tile'))
    if case in ('pending','identity','bound'):
        assert snapshots[1]==(raw[:56]+empty[56:] if split else wanted)
        assert snapshots[2]==wanted
    final=bytes(m.u.mem_read(job,116))
    expected={'CRC':empty,'ready':empty,'tile':empty,'STOP':raw[:56]+empty[56:] if split else wanted}
    assert final==expected.get(case,wanted)
    assert m.get(m.w,kind,'sent',2)==0
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(case=case,polls=len(snapshots),prepared=sum(a!=b for a,b in zip(final,empty)),
                error=m.get(m.w,kind,'error'),ok=bool(ok))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('arm','out'):p.add_argument('--'+k,required=True,type=Path)
    p.add_argument('--split',action='store_true')
    a=p.parse_args()
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),
        rows=[check(a.arm,a.split,c) for c in ('ready','pending','tile','CRC','identity','STOP','bound')]),indent=2)+'\n')
