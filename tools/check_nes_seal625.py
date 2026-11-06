# SPDX-License-Identifier: MIT
"""Compare linked ARM span boundaries at alternating-run and 240B packet edges."""
import argparse
import json
from pathlib import Path
from random import Random

from check_nes_credit623 import ARM, palette_case, sha
from analyze_nes_output615 import packets


def vectors():
    rng=Random(625)
    for n in (1,2,3,61,62,63,64,65,66,81,239,240,241,242,243,304,384,512,2048,4096):
        b=rng.randbytes(n)
        yield b
        yield (b'xy'*((n+1)//2))[:n]
        for at in (0,1,2,17,79,238,239,240,241):
            for length in (62,63,64,65):
                if at+length<=n:
                    yield b[:at]+(b'xy'*33)[:length]+b[at+length:]


def oracle(b):
    # Exact old even-word run and first future 64B alternating run.
    n=len(b)
    limit=min(n,240)
    prefix=2
    while prefix+1<n and b[prefix:prefix+2]==b[:2]:
        prefix+=2
    if prefix>=64:
        return prefix
    return next((i for i in range(1,limit) if i+64<=n and b[i:i+62]==b[i+2:i+64]),limit)


def plan_edge(src,history,prefix_bg,mode):
    m=ARM(src,'normal')
    m.setup()
    for field,value,size in [('early',1,1),('sent',1,2),('bank_history',history,1)]:
        m.put(m.p,'nes_plan200',field,value,size)
    m.endpoint.accepted=1
    exchange=m.endpoint.exchange
    def endpoint(tx,t):
        rx=exchange(tx,t)
        if tx[0]==0xe8:
            if mode=='STOP':m.endpoint.mode='STOP_after_E9'
            if mode=='bad_status':return rx[:-1]+bytes([rx[-1]^1])
        return rx
    m.endpoint.exchange=endpoint
    for i in range(6):
        assert m.emit(int(i>=prefix_bg),30+i,1000+i) and m.endpoint.accepted==1
    ok=m.emit(1,36,1006)
    send=history==2 and prefix_bg==6
    assert bool(ok)==(mode=='normal')
    assert m.endpoint.accepted==1+int(send and ok)
    if send and ok:
        assert m.endpoint.plans==[(0,30+i,1000+i) for i in range(6)]+[(1,36,1006)]
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(history=history,prefix_BG=prefix_bg,mode=mode,E9=m.endpoint.accepted-1)


def test(a):
    palette=bytearray()
    for h,_,_ in packets(a.trace)[957]:
        if h[1]==3:
            b=h[16:]
            palette.extend(b if h[0]==2 else b*(int.from_bytes(h[14:16],'little')//2))
    assert len(palette)==512
    cases=list(vectors())
    results={}
    for name in ('baseline','linear','tables','both','transition','tables-bg'):
        src=a.base if name=='baseline' else a.build/name/'src'
        arm=ARM(src,'normal')
        ptr=0x20018000
        for b in cases:
            arm.u.mem_write(ptr,b)
            assert arm.call('span_piece',[ptr,len(b)])==oracle(b),(name,len(b))
        checks=[palette_case(src,palette,4,mode) for mode in ('normal','bad_crc','bad_count','wrong_identity','STOP_pending','STOP_empty')]
        results[name]=dict(firmware=sha(src/'obj-nes-100/firmware.stm'),vectors=len(cases),palette=checks)
        if name in ('transition','tables-bg'):
            results[name]['plan_edges']=[plan_edge(src,h,b,m) for h,b,m in
                                         [(2,6,'normal'),(1,6,'normal'),(2,5,'normal'),(2,6,'STOP'),(2,6,'bad_status')]]
    a.out.write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('build','base','trace','out'):
        p.add_argument('--'+k,type=Path,required=True)
    test(p.parse_args())
