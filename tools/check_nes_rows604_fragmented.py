"""Check the linked receiver with a legal 224-run row section fragmented across D1 blocks."""
import argparse
from pathlib import Path
import struct

from analyze_nes_wire600 import Receiver
from check_nes_wire600 import pin_packets, pin, read, ROOT


def verify(src,data,probe):
    g=952
    geometry,raw=[data/f'frame{g}.{ext}' for ext in ('geometry','raw')]
    for f in (geometry,raw):pin(f,read(ROOT/'analysis/body581-verification.json')['inputs'][f.name])
    raw=raw.read_bytes()
    geom=bytearray(geometry.read_bytes())
    row_at=2*1056
    legal=bytes([231,0])*112
    geom[row_at:row_at+224]=legal
    rebuilt=[]
    cursor=0
    for prior in pin_packets(probe/'shared',g):
        hdr=b'\x52'+prior[1:3]
        block=bytearray(hdr)
        off=3
        while off<len(prior):
            tag=int.from_bytes(prior[off:off+2],'big')
            k,idx=divmod(tag,8192)
            n=8 if k==0 and idx&4096 else (2,1,7,4,7,1,2,8)[k]
            records=[prior[off:off+n+2]]
            if (tag&0xff00)==0xf900:
                count=(idx&255)+1
                records=[struct.pack('>HH',0xde00,v) for v in legal[cursor:cursor+count]]
                cursor+=count
            for rec in records:
                if len(block)+len(rec)>256:
                    rebuilt.append(bytes(block));block=bytearray(hdr)
                block.extend(rec)
            off+=n+2
        rebuilt.append(bytes(block))
    assert cursor==224
    m=Receiver(src,bytes(128))
    m.receive(rebuilt,bytes(geom),raw,g)
    return dict(rows=cursor,records=cursor,record_B=cursor*4,blocks=len(rebuilt),committed=True)


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('src','data','probe','out'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    a.out.write_bytes((json.dumps(verify(a.src,a.data,a.probe),indent=2)+'\n').encode())
