# SPDX-License-Identifier: MIT
"""Compare linked ordinary-range costs with both the old binary and exact packet pricing."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import Machine, sha


def costs(b, split):
    def repeated(at, n):
        if n<2:return 0
        end=2
        while end+1<n and b[at+end:at+end+2]==b[at:at+2]:end+=2
        return end
    at=total=0
    while at<len(b):
        n=len(b)-at
        part=min(n,240)
        if split:
            run=repeated(at,n)
            if run>=64:
                part=run
            else:
                part=next((i for i in range(1,min(part,n-63)) if repeated(at+i,64)==64),part)
        encoded=2 if part>=4 and part%2==0 and repeated(at,part)==part else part
        total+=471+8*encoded
        at+=part
    return total


def verify(base, new):
    cpus=[Machine(d,bytes(128)) for d in (base,new)]
    data=0x20004000
    vectors=[bytes(range(n)) for n in (0,1,2,3,4,63,64,65,239,240,241,255)]
    vectors.extend([bytes(range(256))*2,bytes(4096),b'AB'*127+b'C',bytes(31)+b'XY'*40+bytes(range(80)),
                    bytes(range(177))+b'CD'*32+b'Z',bytes(range(240))+b'CD'*32,bytes(range(32))+b'XY'*256])
    for b in vectors:
        for cpu in cpus:
            if b:cpu.u.mem_write(data,b)
        expected=[costs(b,s) for s in (False,True)]
        assert [cpus[1].call("wire_cost789",[data,len(b),int(s)]) for s in (False,True)]==expected
        assert [cpu.call("span_cost227",[data,len(b)]) for cpu in cpus]==[min(expected)]*2
    return dict(vectors=len(vectors),firmware=sha(new/"obj-nes-100/firmware.stm"))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("base","new","out"):p.add_argument(k,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(verify(a.base,a.new),indent=2)+"\n")
