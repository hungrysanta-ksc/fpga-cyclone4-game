"""Optimal parse for bundles of eight literal or 12-bit backwards-copy items."""
from collections import defaultdict


def encode(body, prefix=0):
    locations=defaultdict(list)
    options=[]
    for i in range(len(body)):
        key=body[i:i+3]
        best={}
        for j in reversed(locations[key]):
            distance=i-j
            if distance>4096:break
            k=3
            while k<min(18,len(body)-i) and body[j+k]==body[i+k]:k+=1
            for size in range(3,k+1):best.setdefault(size,distance)
            if k==18:break
        options.append(best)
        locations[key].append(i)
    n=len(body)
    cost=[[0]*8 for _ in range(n+1)]
    choices={}
    for i in range(n-1,prefix-1,-1):
        for slot in range(8):
            nxt=(slot+1)%8
            score,size=min([(1+cost[i+1][nxt],1)]+[(2+cost[i+k][nxt],k) for k in options[i]])
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
            out.extend((d&255,((d>>8)<<4)|(size-3)))
        i+=size
        slot=(slot+1)%8
    assert len(out)==prefix+cost[prefix][0]
    return bytes(out)

def decode(stream,prefix,expected):
    """Check exact consumption and overlapping back-references like the loader."""
    out=bytearray(stream[:prefix])
    i=prefix
    while len(out)<expected:
        flags=stream[i]
        i+=1
        for bit in range(8):
            if flags & (1<<bit):
                low,high=stream[i:i+2]
                i+=2
                distance=1+low+((high>>4)<<8)
                length=(high&15)+3
                assert distance<=len(out) and len(out)+length<=expected
                for _ in range(length):
                    out.append(out[-distance])
            else:
                out.append(stream[i])
                i+=1
            if len(out)==expected:break
    assert i==len(stream)
    return bytes(out)
