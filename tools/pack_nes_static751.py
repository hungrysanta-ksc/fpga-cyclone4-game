# SPDX-License-Identifier: MIT
"""Shortest parse with two-byte references to 12 additional pages of decoded WRAM."""
from collections import defaultdict

from nes_rom636 import DEST


def pack(body,prefix):
    positions=defaultdict(list)
    matches=[]
    for i in range(len(body)):
        key=body[i:i+3]
        best={}
        for j in reversed(positions[key]):
            distance=i-j
            kind='near' if distance<=255 else 'medium' if distance<3328 else 'absolute'
            size=3
            while size<min(66,len(body)-i) and body[i+size]==body[j+size]:
                size+=1
            for tag,limit in ((kind,10 if kind=='medium' else 66),('absolute',66)):
                count=min(size,limit)
                if count>best.get(tag,(0,0))[0]:
                    best[tag]=(count,j)
        matches.append(best)
        positions[key].append(i)
    n=len(body)
    cost=[0]*(n+1)
    cost[-1]=1
    choices={}
    for i in reversed(range(prefix,n)):
        candidates=[(1+k+cost[i+k],k,'literal',0) for k in range(1,min(31,n-i)+1)]
        for kind,(end,j) in matches[i].items():
            size=3 if kind=='absolute' else 2
            candidates.extend((size+cost[i+k],k,kind,j) for k in range(3,end+1))
        cost[i],*choices[i]=min(candidates)
    stream=bytearray()
    i=prefix
    while i<n:
        size,kind,j=choices[i]
        if kind=='literal':
            stream.append(size);stream.extend(body[i:i+size])
        elif kind=='near':
            stream.extend((192+size-3,i-j))
        elif kind=='medium':
            distance=i-j
            stream.extend((8*(3+(distance>>8))+size-3,distance&255))
        else:
            stream.append(128+size-3);stream.extend((DEST+j).to_bytes(2,'little'))
        i+=size
    stream.append(0)
    assert len(stream)==cost[prefix]
    return bytes(stream)
