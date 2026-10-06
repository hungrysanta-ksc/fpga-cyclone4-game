# Captured per-plane CHR bank patch packet. SPDX-License-Identifier: MIT.
import struct
from build_nes_fine_scroll import fine_coord,decode as decode_bg
from build_nes_trace_replay import convert,palette
BASE=256
CAPACITY=32
def encode(frame,seq,features,chrdata):
    assert features['ppu_mask']==10 and features['ppu_ctrl']==136
    assert not features['active_ppu_writes'] and not features['scroll_y']
    assert features['immutable_chr_rom'] and len(chrdata)==16384
    fine=features['scroll_x'];assert 0<=fine<8 and 1<=frame<=4
    atlas=convert(chrdata);cells={};seen=set();release=0
    for e in seq:
        pos=fine_coord(e['line'],e['dot'])
        if pos is None:continue
        y,x=pos;off=e['offset'];plane=off%16//8
        assert 0<=y<240 and 0<=x<=32
        assert 0<=off<len(chrdata) and e['tile']==off//16 and off%8==y%8
        assert chrdata[off]==e['value'] and (y,x,plane) not in seen
        seen.add((y,x,plane));release=max(release,e['tick'])
        data,tiles=cells.setdefault((y//8,x),(bytearray(16),set()))
        data[y%8*2+plane]=e['value'];tiles.add(e['tile'])
    assert len(cells)==990 and len(seen)==15840,'missing plane'
    mapping={};patches=[];records=[]
    # Resolve complete current-frame cells first; never consult later frames.
    for key,(data,tiles) in sorted(cells.items()):
        matches=[t for t in sorted(tiles) if atlas[t*16:t*16+16]==data]
        if matches:
            tile=matches[0]
            assert not BASE<=tile<BASE+CAPACITY,'reserved patch slot collision'
        else:
            assert len(patches)<CAPACITY,'patch capacity'
            tile=BASE+len(patches);patches.append(bytes(data))
            records.append(dict(cell=list(key),slot=tile,source_tiles=sorted(tiles)))
        mapping[key]=tile
    main=b''.join(struct.pack('<H',mapping[y,x]) for y in range(30) for x in range(32))
    edge=b''.join(struct.pack('<H',mapping[y,32]) for y in range(30))
    p=struct.pack('<4sBBBBHHII',b'NBP1',1,frame,fine,len(patches),256,240,release,1980)
    return p+main+edge+palette()+b''.join(patches),records
def decode(p,atlas):
    assert len(p)>=2008 and len(atlas)==16384
    magic,version,frame,fine,count,w,h,release,n=struct.unpack('<4sBBBBHHII',p[:20])
    assert (magic,version,w,h,n)==(b'NBP1',1,256,240,1980)
    assert 1<=frame<=4 and 0<=fine<8 and count<=CAPACITY and len(p)==2008+16*count
    tiles=[t[0] for t in struct.iter_unpack('<H',p[20:2000])]
    assert all(t<1024 and not BASE+count<=t<BASE+CAPACITY for t in tiles)
    assert set(t for t in tiles if BASE<=t<BASE+CAPACITY)==set(range(BASE,BASE+count))
    patched=bytearray(atlas);patched[BASE*16:(BASE+count)*16]=p[2008:]
    bg=bytearray(p[:2008]);bg[:4]=b'NFX1';bg[7]=0
    return decode_bg(bytes(bg),bytes(patched))
