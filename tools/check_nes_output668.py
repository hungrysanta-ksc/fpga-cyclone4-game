"""Compare original/candidate linked ARM repeat searches, including packet edges."""
import argparse
import json
import random
from pathlib import Path
from check_nes_game478 import Machine, sha


def reference(b):
    n=len(b);run=2
    while run+1<min(n,4096) and b[run:run+2]==b[:2]:run+=2
    if n<2:run=0
    if run>=64:return run
    end=min(n,240)
    for i in range(1,min(end,n-63)):
        if b[i:i+64]==b[i:i+2]*32:return i
    return end


def check(a):
    rng=random.Random(668)
    cases=[]
    for n in (1,2,3,63,64,65,66,127,128,191,192,239,240,241,255,256,383,384,4095,4096):
        cases.extend([bytes(n),(b'\x12\x34'*2048)[:n],bytes(rng.randrange(256) for _ in range(n))])
    for i in range(1,242):
        # Earliest repeat starts at each possible split point, including 240 cap.
        b=bytearray(rng.randrange(256) for _ in range(384));b[i:i+64]=b'\x31\x82'*32
        cases.append(bytes(b))
    for j in range(2,65):
        b=bytearray(384);b[j]=1;cases.append(bytes(b))
    for _ in range(100):
        n=rng.randrange(1,4097)
        b=bytearray()
        while len(b)<n:
            pair=bytes(rng.randrange(4) for _ in range(2))
            b.extend(pair*rng.randrange(1,40))
        cases.append(bytes(b[:n]))
    result=[]
    for label,src in (('base',a.base),('candidate',a.arm)):
        m=Machine(src,bytes(128));rows=[]
        for data in cases:
            ptr=0x20018000;m.u.mem_write(ptr,data)
            before=m.instructions
            got=m.call('span_piece',[ptr,len(data)])
            assert got==reference(data),(label,len(data),got,reference(data),sha(src/'obj-nes-100/firmware.stm'))
            rows.append(dict(n=len(data),result=got,instructions=m.instructions-before))
        result.append(dict(label=label,firmware=sha(src/'obj-nes-100/firmware.stm'),cases=rows))
    assert [r['result'] for r in result[0]['cases']]==[r['result'] for r in result[1]['cases']]
    out=dict(passed=True,cases=len(cases),runs=result,scope='Actual linked ARM, deterministic boundary/adversarial data; instruction counts are not physical cycles. Full packet/STOP/independent DMA checks are separate.')
    a.out.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(passed=True,cases=len(cases),instruction_totals={r['label']:sum(x['instructions'] for x in r['cases']) for r in result})))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
    check(p.parse_args())
