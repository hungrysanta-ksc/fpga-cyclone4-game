# SPDX-License-Identifier: MIT
"""Reference-format boundaries only; not an ARM/RTL/65816 safety test."""
import json,struct
from nes_abi582 import block,input_blocks,input_packets,restore,canonical,crc,map_restore,map_records

def main():
    positive=0;negative=[]
    for patches in range(8):
        counts=[1056,224,128,128,224,64,patches*256]
        limits=[32768,256,1<<49,1<<32,1<<49,64,64]
        a=[[(i*71+k)%limits[k] for i in range(n)] for k,n in enumerate(counts)]
        for base in (None,[list(x) for x in a]):
            bs=input_blocks(a,base);assert restore(bs,counts,base)==a
            ps=input_packets(a,bs,1 if base is None else 2,0 if base is None else 1)
            assert all(0<len(p)<=256 for p in ps);positive+=1
    def reject(name,fn):
        try:fn()
        except (AssertionError,IndexError,ValueError):negative.append(name);return
        raise AssertionError('accepted '+name)
    a=[[1,2,3],[],[],[],[],[],[]];base=[[1,2,3],[],[],[],[],[],[]]
    b=block(0,3,0,a[0],base[0]);counts=list(map(len,a))
    reject('missing block',lambda:restore([],counts,base))
    reject('duplicate block',lambda:restore([b,b],counts,base))
    reject('delta without base',lambda:restore([b],counts,None))
    corrupt=b[:6]+b'\x80';reject('out-of-range mask',lambda:restore([corrupt],counts,base))
    reject('truncated changed data',lambda:restore([b[:6]+b'\x01'],counts,base))
    wrong=[[0,2,3],[],[],[],[],[],[]]
    assert crc(canonical(restore([b],counts,wrong)))!=crc(canonical(a));negative.append('wrong retained base rejected by frame CRC')
    new=bytearray(4096);new[0]=3;new[15]=7;new=bytes(new)
    rs,masks,_=map_records(new,bytes(4096),[set(),set()],False);digest=crc(b''.join(rs))
    assert map_restore(bytes(4096),rs,masks,digest)==new;positive+=1
    reject('missing map row',lambda:map_restore(bytes(4096),[],masks,crc(b'')))
    reject('duplicate map row',lambda:map_restore(bytes(4096),rs+rs,masks,crc(b''.join(rs+rs))))
    reject('wrong expected map mask',lambda:map_restore(bytes(4096),rs,bytes(64),digest))
    reject('wrong map payload CRC',lambda:map_restore(bytes(4096),rs,masks,digest^1))
    print(json.dumps(dict(passed=True,positive=positive,negative=negative,
        scope='Reference syntax/count/coverage/CRC and raw0..7 fallback. No lifecycle, arbitrary retained-memory fault, STOP, DMA or cycle proof.'),indent=2))

if __name__=='__main__':main()
