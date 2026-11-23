"""Optimal parse for bundles of eight literal or 12-bit backwards-copy items."""
from collections import defaultdict


def encode(body, prefix=0, minimum=3, *, short_pairs=False):
    """In short-pair mode a zero length nibble encodes two bytes 1..16 back.

    Other matches keep the 12-bit distance, with the length nibble sent first
    so the boot loader knows whether to consume the second byte.
    """
    assert minimum in (2,3)
    assert not short_pairs or minimum==2
    locations=defaultdict(list)
    options=[]
    for i in range(len(body)):
        key=body[i:i+minimum]
        best={}
        for j in reversed(locations[key]):
            distance=i-j
            if distance>4096:break
            k=minimum
            while k<min(minimum+15,len(body)-i) and body[j+k]==body[i+k]:k+=1
            for size in range(minimum,k+1):best.setdefault(size,distance)
            if k==minimum+15:break
        if short_pairs and best.get(2,0)>16:
            del best[2]
        options.append(best)
        locations[key].append(i)
    n=len(body)
    cost=[[0]*8 for _ in range(n+1)]
    choices={}
    for i in range(n-1,prefix-1,-1):
        for slot in range(8):
            nxt=(slot+1)%8
            matches=[((1 if short_pairs and k==2 else 2)+cost[i+k][nxt],k) for k in options[i]]
            score,size=min([(1+cost[i+1][nxt],1)]+matches)
            cost[i][slot]=score+(slot==0)
            choices[i,slot]=size
    out=bytearray(body[:prefix]);i=prefix;slot=0
    while i<n:
        if slot==0:
            flags=len(out)
            out.append(0)
        size=choices[i,slot]
        if size==1:out.append(body[i])
        else:
            out[flags]|=1<<slot
            d=options[i][size]-1
            if short_pairs and size==2:
                out.append(d<<4)
            elif short_pairs:
                out.extend((((d>>8)<<4)|(size-minimum),d&255))
            else:
                out.extend((d&255,((d>>8)<<4)|(size-minimum)))
        i+=size
        slot=(slot+1)%8
    assert len(out)==prefix+cost[prefix][0]
    return bytes(out)

def decode(stream,prefix,expected,minimum=3,*,short_pairs=False):
    """Check exact consumption and overlapping back-references like the loader."""
    assert not short_pairs or minimum==2
    out=bytearray(stream[:prefix])
    i=prefix
    while len(out)<expected:
        flags=stream[i]
        i+=1
        for bit in range(8):
            if flags & (1<<bit):
                if short_pairs:
                    high=stream[i]
                    i+=1
                    if high&15:
                        distance=1+stream[i]+((high>>4)<<8)
                        i+=1
                    else:
                        distance=1+(high>>4)
                else:
                    low,high=stream[i:i+2]
                    i+=2
                    distance=1+low+((high>>4)<<8)
                length=(high&15)+minimum
                assert distance<=len(out) and len(out)+length<=expected
                for _ in range(length):
                    out.append(out[-distance])
            else:
                out.append(stream[i])
                i+=1
            if len(out)==expected:break
    assert i==len(stream)
    return bytes(out)
