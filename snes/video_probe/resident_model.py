"""Original two-page residency stimulus; no future-data availability claim.
SPDX-License-Identifier: MIT. Effective events, not NES PPU/MMC3 fetches.
"""
from cache_patterns import pixels,cache_planar,pattern_audit
from video_schedule_model import tile_pixel

def set_keys(set_id):
    assert 0<=set_id<4
    return [(w+8*(set_id%2),set_id//2) for w in range(8)]

def resident_snapshot(frame,fault='none'):
    keys=[list(t) for t in set_keys(0)]+[[255,255] for _ in range(8)]
    masks=[255,0];sets=[0,255]
    for f in range(frame+1):
        page=(f//8)%2;dest=page^1;window=f%8;next_set=(f//8+1)%4
        if window==0:masks[dest]=0;sets[dest]=next_set
        keys[dest*8+window]=list(set_keys(next_set)[window])
        if not(fault=='late' and f%32==7):masks[dest]|=1<<window
    return dict(keys=keys,masks=masks,sets=sets,active_page=page,preload_page=dest)

def working_set_audit():
    frames=[]
    for f in range(32):
        tags=set_keys(f//8)
        keys={(*tags[((x+f)//8+y//8)%8],(((x+f)//8)+(y//8)*7)%64) for y in range(240) for x in range(256)}
        frames.append(dict(state=f,unique_bg_tiles=len(keys),bytes=len(keys)*16))
    assert {f['unique_bg_tiles'] for f in frames}=={256}
    return dict(source_height=240,pixel_referenced_bg_tiles=256,per_set_used_bytes=4096,
        allocated_bg_bytes=16384,allocated_set_bytes=8192,sets_resident=2,
        unannounced_all_new_dma_only_clocks=4096*8,raw_blank_clocks=22*1364,
        early_available_frames=8,required_full_page_uploads=8,frames=frames,
        scope='pixel-referenced synthetic BG keys; no NES fetch capture or sprite CHR update')

def resident_reference(scene,set_id,line_only=False):
    tags=set_keys(set_id);out=[]
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
