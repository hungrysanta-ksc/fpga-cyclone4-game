# SPDX-License-Identifier: MIT
"""Fixed block semantic source format experiment; no product protocol binding."""
import struct
from nes_stream234 import crc

RANGES=[(i*66,66) for i in range(32)]+[(i,min(64,4398-i)) for i in range(2112,4398,64)]


def encode(old,new,raw,serial,generation):
    assert len(old)==len(new)==4398
    cold=serial==1;ops=[];expanded=0
    for index,(at,n) in enumerate(RANGES):
        a,b=old[at:at+n],new[at:at+n]
        if not cold and a==b:continue
        if not cold and index<32 and a[2:]==b[:-2]:
            ops.append(bytes([128|index,1])+b[-2:]);expanded+=66
        elif not cold and index<32 and a[:-2]==b[2:]:
            ops.append(bytes([128|index,255])+b[:2]);expanded+=66
        else:
            changed=[i for i in range(n) if cold or a[i]!=b[i]]
            mask=sum(1<<i for i in changed).to_bytes((n+7)//8,'little')
            ops.append(bytes([index])+mask+bytes(b[i] for i in changed));expanded+=len(changed)
    records=[struct.pack('<2sBBIIIHH',b'N5',1,int(cold),1,0 if cold else serial-1,serial,generation,0)]
    c=crc(records[0])
    for op in ops:records.append(op);c=crc(op,c)
    tail=struct.pack('<HBBHH',65535,0,3,len(ops),expanded);c=crc(tail,c);records.append(tail+struct.pack('<H',c))
    for at in range(0,len(raw),240):
        op=struct.pack('<HB',at,len(raw[at:at+240]))+raw[at:at+240];records.append(op);c=crc(op,c)
    tail=struct.pack('<HBB',65535,0,4);c=crc(tail,c);records.append(tail+struct.pack('<H',c))
    return records


def decode(records,base,serial,generation):
    h=records[0];cold=serial==1
    if h!=struct.pack('<2sBBIIIHH',b'N5',1,int(cold),1,0 if cold else serial-1,serial,generation,0):raise ValueError('admission')
    c=crc(h);out=bytearray(base);last=-1;ops=expanded=0;covered=set();geometry=False;raw=bytearray();ended=False
    for b in records[1:]:
        if ended:raise ValueError('after end')
        if not geometry:
            if b[:4]==b'\xff\xff\x00\x03':
                if len(b)!=10 or struct.unpack_from('<HH',b,4)!=(ops,expanded) or crc(b[:8],c)!=int.from_bytes(b[8:],'little'):raise ValueError('geometry trailer')
                if cold and len(covered)!=4398:raise ValueError('cold coverage')
                c=crc(b[:8],c);geometry=True;continue
            index=b[0]&127
            if index>=len(RANGES) or index<=last:raise ValueError('block order')
            at,n=RANGES[index];last=index;ops+=1
            if b[0]&128:
                if cold or index>=32 or len(b)!=4 or b[1] not in (1,255):raise ValueError('shift')
                old=bytes(out[at:at+66]);out[at:at+66]=old[2:]+b[2:] if b[1]==1 else b[2:]+old[:-2]
                expanded+=66;covered.update(range(at,at+66))
            else:
                mbytes=(n+7)//8
                if len(b)<1+mbytes:raise ValueError('mask length')
                mask=int.from_bytes(b[1:1+mbytes],'little')
                if not mask or mask>>n:raise ValueError('mask bits')
                if len(b)!=1+mbytes+mask.bit_count():raise ValueError('literal length')
                it=iter(b[1+mbytes:])
                for i in range(n):
                    if mask>>i&1:out[at+i]=next(it);covered.add(at+i);expanded+=1
            c=crc(b,c)
        elif b[:4]==b'\xff\xff\x00\x04':
            if len(b)!=6 or crc(b[:4],c)!=int.from_bytes(b[4:],'little'):raise ValueError('raw end')
            ended=True
        else:
            if len(b)<3:raise ValueError('raw header')
            at,n=struct.unpack_from('<HB',b)
            if at!=len(raw) or not 0<n<=240 or len(b)!=3+n or at+n>1792 or any(x>=64 for x in b[3:]):raise ValueError('raw bounds')
            raw+=b[3:];c=crc(b,c)
    if not ended:raise ValueError('missing end')
    return bytes(out),bytes(raw)
