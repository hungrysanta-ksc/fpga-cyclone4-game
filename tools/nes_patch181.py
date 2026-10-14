# SPDX-License-Identifier: MIT
"""Prototype SNES row overlay format; not a deployed packet/client change.

Normal rows use mode0 BG1+OBJ. Patched rows use mode3 BG1 only, with
already-composited NES color indices at CGRAM64..127. The original banked169
BG/OBJ/map regions remain untouched. Each bank's unused gap holds patch CHR
and a separate 32x32 map. No cartridge SRAM, full pixel frame or runtime heap.
"""
import struct
MAX_ROWS=7
LAYOUTS=[dict(bg=0,obj=0x4000,map=0x6000,patch=0x5000,patch_map=0x7000),
         dict(bg=0xc000,obj=0x8000,map=0xa000,patch=0x9000,patch_map=0xb000)]

def encode(rows,slot):
    if slot not in (0,1) or len(rows)>MAX_ROWS:raise ValueError('bounded patch rows/bank')
    ids=[y for y,_ in rows]
    if ids!=sorted(set(ids)) or any(y<0 or y>=224 for y in ids):raise ValueError('row ordering')
    if any(len(p)!=256 or any(c>=64 or c<0 for c in p) for _,p in rows):raise ValueError('aligned6bit row')
    layout=LAYOUTS[slot];tiles=bytearray(2048)
    for f,(_,pixels) in enumerate(rows):
        for x,c in enumerate(pixels):
            value=64+c # never transparent; preserves NES color0 as a real color
            for plane in range(8):
                at=(x//8)*64+(plane//2)*16+f*2+plane%2
                tiles[at]|=((value>>plane)&1)<<(7-x%8)
    first=((layout['patch']-layout['bg'])&65535)//64
    tilemap=b''.join(struct.pack('<H',first+x) for x in range(32))+bytes(1984)
    # Two 1KiB blocks are intentional: BG1SC uses32x32 (2048 bytes).
    # Fits 7000..77ff / b000..b7ff and leaves the adjacent bank untouched.
    descriptors=[];slots={y:i for i,y in enumerate(ids)}
    for y in range(224):
        patched=y in slots
        mode=3 if patched else 0
        map_address=layout['patch_map'] if patched else layout['map']
        scroll_y=(slots[y]-y-1)&1023 if patched else 1023
        descriptors.append((bytes([mode,0,(map_address//2048)*4+(0 if patched else 1),0]),
                            bytes([1 if patched else 17,0,0,0]),struct.pack('<HH',0,scroll_y)))
    def table(index):
        out=bytearray();y=0
        while y<224:
            end=y+1
            while end<224 and end-y<127 and descriptors[end][index]==descriptors[y][index]:end+=1
            out.append(end-y);out.extend(descriptors[y][index]);y=end
        out.append(0);return bytes(out)
    return dict(layout=layout,chr=bytes(tiles),map=tilemap,hdma=[table(i) for i in range(3)],rows=ids)
