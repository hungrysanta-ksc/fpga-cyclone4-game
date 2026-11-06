# SPDX-License-Identifier: MIT
"""Exercise publication, real E0 identity checks, wrap, STOP and report bounds on the linked M4."""
import argparse
import hashlib
import json
from pathlib import Path

from check_nes_supply485_arm import ARM, crc, sha


def palette_case(src, palette, samples, mode, bg=4):
    m=ARM(src,'normal')
    m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.s,'nes_native_sink165','bg_next',bg,2)
    for field in ('ending','finished'):
        m.put(m.p,'nes_plan200',field,1,1)
    for field in ('sent','retired'):
        m.put(m.w,'nes_sink_window184',field,65534,2)
    packets=[]
    observations=[]
    m.endpoint.accepted=1
    def transfer(tx,clock):
        if tx[0]==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            packets.append(tx[1:-2])
            return bytes(len(tx))
        assert tx[0]==0xe0 and len(packets)==2
        complete=bool(observations)
        observations.append(complete)
        reply=bytearray(20)
        reply[1:3]=bytes([0xf7,2 if complete else 3])
        reply[3:7]=bytes([0,0,0,0] if complete else [0,0,255,255])
        prev=packets[1 if complete else 0]
        reply[7:19]=bytes([0,prev[0]])+prev[2:10]+b'\x65\x9a'
        if mode=='bad_count':reply[4]=1
        if mode=='wrong_identity' and complete:reply[15]^=1
        reply[19]=crc(reply[1:19],8,7,0)
        if mode=='bad_crc':reply[19]^=1
        if (mode=='STOP_pending' and not complete) or (mode=='STOP_empty' and complete):
            m.endpoint.mode='STOP_after_E9'
        return bytes(reply)
    m.endpoint.exchange=transfer
    ptr=m.video+m.layout['nes_native_video165']['cgram']
    m.u.mem_write(ptr,bytes(palette))
    ok=m.call('span',[m.s,3,0,ptr,512])
    assert bool(ok)==(mode=='normal')
    offsets=[int.from_bytes(b[10:12],'little') for b in packets]
    assert offsets==([0,32,128,360] if ok else [0,32])
    if ok:
        assert len(observations)==(samples+1 if samples else 0)
        buf=bytearray()
        for p in packets:
            assert p[1]==3 and len(buf)==int.from_bytes(p[10:12],'little')
            data=p[16:]
            assert len(data)==int.from_bytes(p[12:14],'little')
            buf.extend(data if p[0]==2 else data*(int.from_bytes(p[14:16],'little')//2))
        assert buf==palette
    else:
        assert m.get(m.s,'nes_native_sink165','error') and not m.get(m.s,'nes_native_sink165','displayed')
    return dict(mode=mode,bg_units=bg,offsets=offsets,E0_empty=observations)


def report_vectors(src):
    m=ARM(src,'normal')
    for name,n in [('nes_startup222',56),('nes_plan215',30),('nes_boot214',24),
                   ('nes_budget210',1104),('nes_cost471_ops',192),('nes_cost474_waits',60)]:
        m.u.mem_write(m.data_symbols[name],bytes((j*37+9)%256 for j in range(n)))
    ptr=0x20018000
    bound=8192
    stack=0x2001d000
    pattern=b'\xa5'
    results=[]
    depth=0
    for sampled in (0,1):
        m.u.mem_write(m.data_symbols['report_valid'],bytes([sampled]))
        def render(size):
            nonlocal depth
            m.u.mem_write(ptr-1,pattern*(bound+2))
            m.u.mem_write(stack,pattern*4096)
            n=m.call('nes_budget210_format',[ptr,size])
            memory=bytes(m.u.mem_read(ptr-1,bound+2))
            assert memory[0]==165 and memory[size+1:]==pattern*(bound+1-size)
            used=bytes(m.u.mem_read(stack,4096)).lstrip(pattern)
            depth=max(depth,len(used))
            return n,memory[1:size+1]
        n,buf=render(bound)
        assert 0<n<bound and buf[n]==0 and (b'cost_poll_2=' in buf)==bool(sampled)
        for size in (0,1,31,buf.index(b'boot_schema'),buf.index(b'plan_schema')+3,n-1,n,n+1,bound):
            count,out=render(size)
            assert count==(n if size>n else 0xffffffff)
            results.append([sampled,size,count,hashlib.sha256(out).hexdigest()])
    return results,depth


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','build','trace','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    palette=bytearray()
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        b=bytes.fromhex(json.loads(line)[2])
        if b[1]==3 and int.from_bytes(b[8:10],'little')==957:
            assert len(palette)==int.from_bytes(b[10:12],'little')
            palette.extend(b[16:] if b[0]==2 else b[16:]*(int.from_bytes(b[14:16],'little')//2))
    assert len(palette)==512
    base,depth=report_vectors(a.base)
    proof=dict(report_vectors=base,baseline_stack_touched_B=depth,candidates={})
    for mode,checks in [('drain-report',1),('snapshots',4),('small-snapshots',4)]:
        src=a.build/mode/'src'
        rows=[palette_case(src,palette,checks,f) for f in ('normal','bad_crc','bad_count','wrong_identity','STOP_pending','STOP_empty')]
        if mode=='small-snapshots':
            rows.extend(palette_case(src,palette,k,'normal',bg) for bg,k in ((1,0),(2,4),(5,0)))
        vectors,high=report_vectors(src)
        assert vectors==base
        proof['candidates'][mode]=dict(edges=rows,stack_touched_B=high,arm=sha(src/'obj-nes-100/firmware.stm'))
    a.out.write_text(json.dumps(proof,indent=2)+'\n')
