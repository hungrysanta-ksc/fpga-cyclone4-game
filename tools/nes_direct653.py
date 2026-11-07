"""Independent direct-cell packet oracle. Non-map records keep their original wire ABI."""
import struct
from nes_geometry650 import legacy,pack


def map_block(cells,start,generation):
    packed=pack(cells,start,generation)
    pos=10
    while pos<len(packed):
        command=packed[pos]
        if command>=128:return packed
        pos+=1+2*(command+1)
    payload=bytearray()
    for i in range(0,len(cells),4):
        group=cells[i:i+4]
        value=sum(cell<<(15*j) for j,cell in enumerate(reversed(group)))
        payload.extend(struct.pack(">HHQ",0x1000+start+i,generation,(len(group)<<60)|value))
    return bytes(payload)


def encode(geometry,raw,generation):
    original,counts,arrays=legacy(geometry,raw,generation)
    maps=arrays[0];out=[];start=0
    while start<len(maps):
        cells=maps[start:start+(80 if not start else 84)]
        out.append((original[0][:12] if not start else b"")+map_block(cells,start,generation))
        start+=len(cells)
    block=bytearray()
    for packet in original:
        pos=0
        while pos<len(packet):
            tag=int.from_bytes(packet[pos:pos+2],"big");kind,index=tag>>13,tag&8191
            width=8 if kind==0 and index&4096 else (2,1,7,4,7,1,2,8)[kind]
            record=packet[pos:pos+4+width];pos+=len(record)
            if kind==0 or tag==0xe000 or tag>>8==0xd0:continue
            block.extend(record)
            if len(block)>244 or (kind==7 and 0<index<2048):
                out.append(bytes(block));block.clear()
    assert not block and max(map(len,out))<=256
    return out,counts,arrays
