"""Exercise the linked ARM SEAL sender and independently decode section 5."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_reuse635_arm import Sender
from nes_raw506 import sha


def emit(src, hdma_size, count, zeros, reject=False, reuse=False, obj=False):
    m = Sender(src, 'normal')
    sink = m.test_sink = 0x20015800
    m.heads = []
    m.reject_final = reject
    for kind, address, fields in (
        ('nes_native_sink165', sink, [('exchange',m.callback|1,4),('enqueue',m.callback|1,4),
                                        ('serial',1,4),('generation',905,2),('state',1,1)]),
        ('nes_resident211', m.resident, [('prepared',1,1),('open',1,1),('serial',1,4),('generation',905,2)]),
        ('nes_native_video165', m.video, [('valid',1,1),('generation',905,2),('bg_count',1,2),
                                           ('hdma_size',hdma_size,2),('display_mask',0x1e,1),('patch_count',count,1)]),
    ):
        for name, value, width in fields:
            m.put(address, kind, name, value, width)
    if reuse:
        m.put(sink,'nes_native_sink165','ack635',3|(4<<32),8)
        m.put(sink,'nes_native_sink165','displayed',1,1)
        m.put(m.resident,'nes_resident211','displayed',1,1)
        for address,kind in ((sink,'nes_native_sink165'),(m.resident,'nes_resident211')):
            m.put(address,kind,'serial',5,4)
    if obj:
        m.put(sink,'nes_native_sink165','obj_next',1,2)
    addresses = ([tile*64+plane*16+row*2+bit for plane in range(3) for row in range(count)
                  for tile in range(32) for bit in range(2)] if count <= 2 else list(range(2048)))
    raw = bytes(0 if i < zeros else 1+i%251 for i in range(len(addresses)))
    canonical = bytearray([0xcc])*2048
    for offset, value in zip(addresses, raw):
        canonical[offset] = value
    tables = bytes(i%251 for i in range(243))
    lengths = struct.pack('<HHH',21,35,81)
    m.u.mem_write(m.video, bytes(canonical)+tables+b'\xcd'+lengths)
    hdma = bytes([0x39])*hdma_size
    m.u.mem_write(m.video+m.layout['nes_native_video165']['hdma'], hdma)
    ok = m.call('nes_sink212_seal',[sink,m.video,m.resident])
    assert bool(ok) == (not reject) and m.before_final == (3|(4<<32) if reuse else 0)
    assert m.get(sink,'nes_native_sink165','ack635',4) == ((3 if reject else 5) if reuse else int(not reject))
    restored = bytearray()
    sections = []
    for packet in m.heads:
        if packet[1] != 5:
            continue
        op, offset, length, expanded = packet[0], *struct.unpack_from('<HHH',packet,10)
        body = packet[16:]
        assert offset == len(restored) and len(body) == length
        if op in (4,5):
            assert length == 2 and expanded%2 == 0
            body *= expanded//2
        else:
            assert op == 2 and expanded == 0
        sections.append((op,offset,len(body)))
        restored.extend(body)
    expected = hdma if not count else hdma.ljust(1121,b'\0')+raw+tables+lengths
    assert restored == expected
    assert m.heads[-1][0] == 3 and int.from_bytes(m.heads[-1][26:28],'little') == len(expected)
    return sections


def run(base, arm, out, after_obj):
    results = []
    for size,count,zeros in [(21,2,n) for n in (0,1,2,65,66,383,384)]+[
            (16,2,66),(871,1,192),(876,1,192),(881,2,66),(1121,3,2),
            (1,3,2048),(21,3,2047),(21,0,0)]:
        b = emit(base,size,count,zeros,reuse=after_obj,obj=after_obj)
        c = emit(arm,size,count,zeros,reuse=after_obj,obj=after_obj)
        pad = 1121-size
        if count and pad>240 and pad%2==0 and zeros>=2:
            assert (5,size,pad+(zeros & ~1)) in c
        else:
            assert b == c
        results.append(dict(scroll=size,patches=count,zero_prefix=zeros,old=b,new=c))
    if after_obj:
        for reuse,obj in ((False,False),(False,True),(True,False)):
            assert emit(arm,21,2,66,reuse=reuse,obj=obj)==emit(base,21,2,66,reuse=reuse,obj=obj)
    emit(arm,21,2,66,reject=True,reuse=after_obj,obj=after_obj)
    out.write_text(json.dumps(dict(passed=True,firmware=sha(arm/'obj-nes-100/firmware.stm'),
                                   cases=results,rejected_final_preserves_history=True),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','arm','out'):
        p.add_argument(k,type=Path)
    p.add_argument('--after-obj',action='store_true')
    a=p.parse_args()
    run(a.base,a.arm,a.out,a.after_obj)
