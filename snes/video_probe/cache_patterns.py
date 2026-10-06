"""Original, address-distinct CHR fixtures and independent coordinate reference.
SPDX-License-Identifier: MIT. Effective bank events, not an MMC3/PPU model.
"""
import hashlib
from functools import lru_cache
from video_schedule_model import tile_pixel

@lru_cache(None)
def pixels(bank,generation,tile):
    assert 0<=bank<16 and 0<=generation<2 and 0<=tile<64
    identity=((generation*16+bank)*64+tile)
    digest=hashlib.sha256(identity.to_bytes(2,'little')+b'NES cache original 003').digest()
    data=[(digest[n//4]>>((n%4)*2))&3 for n in range(64)]
    # Six leading 2bpp pixels encode all eleven address/generation identity bits.
    data[:6]=[(identity>>(2*n))&3 for n in range(6)]
    return tuple(data)

@lru_cache(None)
def cache_planar(bank,generation,tile):
    data=pixels(bank,generation,tile);result=bytearray()
    for y in range(8):
        for b in (0,1):result.append(sum(((data[y*8+x]>>b)&1)<<(7-x) for x in range(8)))
    return bytes(result)

def schedule_state(i):
    tags=[(w,1) for w in range(8)];old=None;new=None
    for step in range(i+1):
        w=step%8;phase=step//8
        old=tags[w];new=(w+(8 if phase<2 else 0),phase%2);tags[w]=new
    return tags,old,new

def pattern_audit():
    data=[cache_planar(b,g,t) for b in range(16) for g in range(2) for t in range(64)]
    assert len(data)==len(set(data))==2048
    # Verify planar encoding independently by decoding every bit.
    for b in range(16):
        for g in range(2):
            for t in range(64):
                raw=cache_planar(b,g,t)
                decoded=tuple(((raw[y*2]>>(7-x))&1)|(((raw[y*2+1]>>(7-x))&1)<<1) for y in range(8) for x in range(8))
                assert decoded==pixels(b,g,t)
    return dict(unique_tiles=2048,total_tiles=2048,bank_alias_pairs=0,planar_roundtrip=True,atlas_sha256=hashlib.sha256(b''.join(data)).hexdigest())

def cache_reference(scene,i,line_only=False):
    tags,_,_=schedule_state(i);out=[]
    for y in range(240):
        active=[sp for sp in scene.sprites if sp['y']<=y<sp['y']+sp['height']][:8]
        for x in range(256):
            sx=(x+scene.frame)%512;tx=sx//8;ty=y//8
            bank,gen=tags[(tx+ty)%8];tile=(tx+ty*7)%64
            bg=pixels(bank,gen,tile)[(y%8)*8+sx%8]
            pal=17 if y>119 or (y==119 and x>=123 and not line_only) else 0
            c=(bg+4*((tx//2+ty//2)%4)+pal)%64 if bg else 0
            for sp in active:
                if sp['x']<=x<sp['x']+8:
                    sy=y-sp['y'];st=(sp['tile']&~1)+sy//8 if sp['height']==16 else sp['tile']
                    p=tile_pixel(sp['bank'],st,x-sp['x'],sy%8)
                    if p:
                        if not(sp['behind'] and bg):c=(32+p+(sp['tile']%4)*4+pal)%64
                        break
            out.append(c)
    return out
