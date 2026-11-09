"""Optimal byte-cost parse for the unchanged636 packed ROM decoder.

No new CPU opcode, no target table, no CRC removal. Enumerate every legal
literal/ref length; retain exact693 body and select the largest fitting prefix.
"""
import argparse,json
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch
import nes_rom636 as codec
from nes_raw506 import sha

def optimal(body,prefix):
    n=len(body);positions=defaultdict(list);refs=[]
    for at in range(n):
        short=absolute=0;shortpos=abspos=0
        for prev in reversed(positions[body[at:at+3]]):
            length=3
            while length<min(66,n-at) and body[prev+length]==body[at+length]:length+=1
            if length>absolute:absolute,abspos=length,prev
            if at-prev<=255 and length>short:short,shortpos=length,prev
            if absolute==66 and (short==66 or at-prev>255):break
        refs.append((short,shortpos,absolute,abspos));positions[body[at:at+3]].append(at)
    cost=[10**9]*(n+1);choice=[None]*n;cost[n]=1
    for at in range(n-1,prefix-1,-1):
        for length in range(1,min(127,n-at)+1):
            c=1+length+cost[at+length]
            if c<cost[at]:cost[at]=c;choice[at]=('literal',length,0)
        short,sp,absolute,ap=refs[at]
        for kind,bound,prev,extra in [('short',short,sp,2),('absolute',absolute,ap,3)]:
            for length in range(3,bound+1):
                c=extra+cost[at+length]
                if c<cost[at]:cost[at]=c;choice[at]=(kind,length,prev)
    out=bytearray();at=prefix
    while at<n:
        kind,length,prev=choice[at]
        if kind=='literal':out.append(length);out.extend(body[at:at+length])
        elif kind=='short':out.extend((192+length-3,at-prev))
        else:out.append(128+length-3);out.extend((codec.DEST+prev).to_bytes(2,'little'))
        at+=length
    out.append(0);assert len(out)==cost[prefix]
    return bytes(out)

def run(a):
    body=(a.client/'body.bin').read_bytes()
    assert sha(a.client/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
    with patch.object(codec,'pack',optimal):
        codec.build(a.raw635,a.out,edit_body=lambda b,l:body,allow_extension=True)
    (a.out/'labels.json').write_bytes((a.client/'labels.json').read_bytes())
    info=json.loads((a.out/'build.json').read_text());info.update(candidate='longrun694',body_capacity=0x1900,body_free=0x1900-len(body),copy_verified_bytes=len(body),new_persistent_WRAM_B=0,body_identical693=True,body_SHA256=sha(a.out/'body.bin'))
    (a.out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    print('CPU694 unchanged body',len(body),'prefix',info['prefix_B'],'encoded',info['encoded_B'],'free',info['physical_free_B'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','raw635','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
