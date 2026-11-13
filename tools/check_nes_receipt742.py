"""Check cumulative map retirement and pending bulk ownership on linked Cortex-M4."""
import argparse
import json
import struct
from pathlib import Path
from check_nes_handoff678 import Handoff, crc, sha


def check(src, case, original):
    m=Handoff(src,'STOP_after_input' if case=='STOP' else 'normal')
    m.setup()
    sent=0 if case=='wrap' else 17
    until=(sent-1)&65535
    if case in ('expired','future'):
        until=(sent+{'expired':-5,'future':1}[case])&65535
    for k,v,n in [('ending',1,1),('started',1,1),('generation',907,2),('bank_history',2,1),
                  ('bulk_valid',1,1),('bulk_pending',1,1),('bulk_until',until,2)]:
        m.put(m.p,'nes_plan200',k,v,n)
    old=bytes((1,0))+struct.pack('<HHHI',48,0,907,1)
    m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],old)
    for k,v,n in [('sent',sent,2),('retired',(sent-2)&65535,2),('ever_sent',1,1),('wait',m.callback|1,4)]:
        m.put(m.w,'nes_sink_window184',k,v,n)
    last=bytes((2,2))+struct.pack('<HIH',1,1,907)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
    m.put(m.s,'nes_native_sink165','sequence',2,2)
    samples=0
    def exchange(tx,clock):
        nonlocal samples
        m.ops.append(tx[0])
        r=bytearray(len(tx))
        if tx[0]==0xe8:
            r[1:3]=bytes((0xd7,4))
            r[6:18]=bytes((1,1))+struct.pack('<HHHI',288,2720,907,2)
            r[19]=crc(r[1:19],8,7,0)^(case=='bad_descriptor_crc')
        elif tx[0]==0xe0:
            samples+=1
            stale=case=='pending' and samples==1
            r[1:3]=bytes((0xf7,3 if stale else 2))
            r[3:7]=struct.pack('>HH',sent,(sent-int(stale))&65535)
            r[7:19]=bytes((0,2))+last[2:]+bytes((0x65,0x9a))
            if stale or case=='wrong_map':
                r[9]^=1
            r[19]=crc(r[1:19],8,7,0)^(case=='bad_receipt_crc')
        else:
            assert tx[:3]==bytes((0xe1,7,1)) and tx[17:21]==struct.pack('<I',2)
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
        return bytes(r)
    m.endpoint.exchange=exchange
    ok=m.call('nes_plan200_progress',[m.p,0])
    positive=case in ('normal','pending','wrap')
    assert bool(ok)==positive,(case,m.ops)
    assert m.ops.count(0xe1)==int(positive)
    if positive:
        expected_polls=2 if original or case=='pending' else 1
        assert samples==expected_polls
        assert m.get(m.p,'nes_plan200','bulk_until',2)==(sent+1)&65535
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return {'case':case,'SPI':[hex(x) for x in m.ops],'submitted':bool(ok)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--original',action='store_true')
    a=p.parse_args()
    cases=('normal','pending','wrap','expired','future','wrong_map','bad_descriptor_crc','bad_receipt_crc','STOP')
    rows=[check(a.arm,c,a.original) for c in cases]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
