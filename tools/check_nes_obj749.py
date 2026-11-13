# SPDX-License-Identifier: MIT
"""Execute the page-start handoff with an owned BG followed by the actual-size OBJ."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_handoff678 import Handoff, crc, sha


def check(src, case, query_first=False):
    m=Handoff(src,'normal')
    m.setup()
    sent=0 if case=='wrap' else 10
    for k,v,n in [('ending',1,1),('started',1,1),('generation',907,2),('bank_history',2,1),
                  ('bulk_valid',1,1),('bulk_pending',1,1),('bulk_until',sent,2)]:
        m.put(m.p,'nes_plan200',k,v,n)
    old=bytes((1,0))+struct.pack('<HHHI',48,0,907,1)
    m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],old)
    for k,v,n in [('sent',sent,2),('retired',(sent-1)&65535,2),('ever_sent',1,1),('wait',m.callback|1,4)]:
        m.put(m.w,'nes_sink_window184',k,v,n)
    last=bytes((7,0))+struct.pack('<HIH',1,1,907)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
    m.put(m.s,'nes_native_sink165','sequence',2,2)
    def exchange(tx,clock):
        m.ops.append(tx[0])
        r=bytearray(len(tx))
        if tx[0]==0xe0:
            stale=case=='pending' and m.ops.count(0xe0)==1
            r[1:3]=bytes((0xf7,3 if stale else 2))
            r[3:7]=struct.pack('>HH',sent,(sent-stale)&65535)
            r[7:19]=bytes((0,7))+last[2:]+bytes((0x65,0x9a))
            if case=='wrong_BG':r[9]^=1
            r[19]=crc(r[1:19],8,7,0)^(case=='bad_receipt_crc')
            if case=='STOP':m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
        elif tx[0]==0xe8:
            r[1:3]=bytes((0xd7,4))
            r[6:18]=bytes((1,1))+struct.pack('<HHHI',288,2720,908 if case=='wrong_generation' else 907,2)
            if m.ops.count(0xe8)==1:
                if case=='previous_BG':r[6:18]=old
                if case=='previous_BG_mutated':r[6:18]=old[:2]+bytes((32,))+old[3:]
                if case=='not_ready':r[6:18]=bytes(12)
            r[19]=crc(r[1:19],8,7,0)^(case=='bad_descriptor_crc')
        else:
            assert tx[:3]==bytes((0xe1,7,1)) and tx[17:21]==struct.pack('<I',2)
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
        return bytes(r)
    m.endpoint.exchange=exchange
    ok=bool(m.call('nes_plan749_after_bg',[m.p]))
    if case=='not_ready':
        assert query_first and ok and m.ops==[0xe8,0xe0] and not m.get(m.p,'nes_plan200','bulk_pending')
        assert not m.get(m.s,'nes_native_sink165','displayed')
        return dict(case=case,submitted=False,SPI=m.ops)
    assert ok==(case in ('normal','pending','wrap','previous_BG')) and m.ops.count(0xe1)==int(ok),(case,m.ops)
    if ok:
        receipts=[0xe0]*(2 if case=='pending' else 1)
        expected=([0xe8]+receipts if query_first else receipts+[0xe8])+[0xe1]
        if case=='previous_BG':expected=[0xe8,0xe0,0xe8,0xe1]
        assert m.ops==expected
        assert m.get(m.p,'nes_plan200','bulk_pending') and m.get(m.p,'nes_plan200','bulk_until',2)==((sent+1)&65535)
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(case=case,submitted=ok,SPI=m.ops)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--query-first',action='store_true')
    a=p.parse_args()
    cases=('normal','pending','wrap','wrong_BG','bad_receipt_crc','bad_descriptor_crc','wrong_generation','STOP')
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),
                                     rows=[check(a.arm,c,a.query_first) for c in cases]),indent=2)+'\n')
