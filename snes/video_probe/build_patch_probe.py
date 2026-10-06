"""Mode1 BG3 2bpp + BG1 sparse 4bpp patch experiment. SPDX-License-Identifier: MIT.
Original synthetic pixels only. Fixed preloaded scene, not real-time conversion.
"""
from pathlib import Path
import argparse,json,struct,hashlib
from build_probe import Asm,color,rgb,planar,scenes,reference

def encode4(pixels):
    out=bytearray()
    for pair in (0,2):
        for y in range(8):
            out.extend(sum(((pixels[y*8+x]>>b)&1)<<(7-x) for x in range(8)) for b in (pair,pair+1))
    return bytes(out)

def build(out,diagnostic=False,omit_patch=False):
    out.mkdir(parents=True,exist_ok=False)
    scene=next(s for s in scenes() if s.name=='dot_palette');pixels=reference(scene)
    base=reference(scene,line_only=True)
    changed=sorted({(i%256//8,i//256//8) for i,(a,b) in enumerate(zip(pixels,base)) if a!=b})
    groups=[];patches=[]
    for tx,ty in changed:
        data=[pixels[(ty*8+y)*256+tx*8+x] for y in range(8) for x in range(8)];colors=set(data)
        assert len(colors)<=15
        group=next((i for i,g in enumerate(groups) if len(g|colors)<=15),None)
        if group is None:group=len(groups);groups.append(set())
        groups[group]|=colors;patches.append((tx,ty,data,group))
    assert len(groups)<=6  # BG1 palettes 2..7, first 32 entries reserved for BG3.
    palette=[0]*256
    for j in range(16):
        palette[j]=color(j) if j%4 else 0
        palette[16+j]=color((j+17)%64) if j%4 else 0
    lookup=[]
    for i,g in enumerate(groups):
        mapping={c:n+1 for n,c in enumerate(sorted(g))};lookup.append(mapping)
        for c,n in mapping.items():palette[(i+2)*16+n]=color(c)
    patchtiles=bytearray(32);patchmap=bytearray(2048)
    for n,(tx,ty,data,g) in enumerate(patches,1):
        patchtiles.extend(encode4([lookup[g][c] for c in data]))
        if not omit_patch:struct.pack_into('<H',patchmap,(ty*32+tx)*2,n|((g+2)<<10))
    bgtiles=b''.join(planar(bank,tile,0) for bank in range(8) for tile in range(64))
    maps=[]
    for alternate in (0,4):
        m=bytearray()
        for page in range(2):
            for ty in range(32):
                for lx in range(32):
                    tx=page*32+lx;bank=(tx+ty)%8;tile=(tx+ty*7)%64;pal=(tx//2+ty//2)%4+alternate
                    m.extend(struct.pack('<H',bank*64+tile+(pal<<10)))
        maps.append(m)
    rom=bytearray([0xff])*32768
    # All static graphics fit inside one LoROM bank; no cart mapper needed.
    blobs=[(0xa000,0x4000,bgtiles,0x18,1),(0xc000,0,maps[0],0x18,1),
           (0xd000,0x1000,maps[1],0x18,1),(0xe000,0x0800,patchmap,0x18,1),
           (0xe800,0x3000,patchtiles,0x18,1),
           (0xeb00,0,b''.join(struct.pack('<H',v) for v in palette),0x22,2)]
    for addr,dst,data,t,m in blobs:
        assert addr+len(data)<0xef00
        rom[addr-0x8000:addr-0x8000+len(data)]=data
    rom[0x6f00:0x6f05]=bytes([120,1,119,0x11,0])
    a=Asm(0x7e2000);a.emit(0x78,0xe2,0x20,0xc2,0x10)
    for r,v in [(0x2100,0x80),(0x4200,0),(0x420c,0),(0x2105,1),(0x2107,8),(0x2109,1),
                (0x210b,3),(0x210c,4),(0x212c,5),(0x212d,0),(0x2130,0),(0x2131,0),(0x2133,4),(0x2115,0x80)]:a.store(r,v)
    for r,v in [(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,3),
                (0x2111,6),(0x2111,0),(0x2112,255),(0x2112,3)]:a.store(r,v)
    for src,dst,data,target,mode in blobs:
        if target==0x18:a.store(0x2116,dst&255);a.store(0x2117,dst>>8)
        else:a.store(0x2121,0)
        for r,v in [(0x4300,mode),(0x4301,target),(0x4302,src&255),(0x4303,src>>8),(0x4304,0),
                    (0x4305,len(data)&255),(0x4306,len(data)>>8),(0x420b,1)]:a.store(r,v)
    for r,v in [(0x4310,0),(0x4311,9),(0x4312,0),(0x4313,0xef),(0x4314,0)]:a.store(r,v)
    a.label('wait_active');a.absolute(0xad,0x4212);a.branch(0x30,'wait_active')
    a.label('wait_blank');a.absolute(0xad,0x4212);a.branch(0x10,'wait_blank')
    a.store(0x420c,2);a.store(0x2100,15);a.store(0x1ff0,0xa5)
    if diagnostic:a.store(0x1ff1,0xd1)
    a.label('loop');a.branch(0x80,'loop');body=a.finish();rom[0x1000:0x1000+len(body)]=body
    boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a)
    boot.emit(0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
    boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
    boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
    code=boot.finish();rom[:len(code)]=code
    rom[0x7fc0:0x7fd5]=b'NES P1 MODE1 PATCH   '.ljust(21,b' ')[:21]
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for p in range(0x7fe0,0x8000,2):rom[p:p+2]=struct.pack('<H',0x8000)
    checksum=sum(rom)&65535;rom[0x7fdc:0x7fe0]=struct.pack('<HH',checksum^65535,checksum)
    (out/'probe.sfc').write_bytes(rom)
    (out/'expected.json').write_text(json.dumps(dict(width=256,height=240,pixels=pixels,lut=[rgb(c) for c in range(64)])))
    manifest=dict(candidate='NES-P1-MODE1-001',diagnostic=diagnostic,omit_patch=omit_patch,rom_sha256=hashlib.sha256(rom).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),patch_tiles=len(patches),patch_palettes=len(groups),
        patch_tile_bytes=len(patches)*32,patch_map_delta_bytes=len(patches)*2,patch_palette_bytes=sum(len(g)*2 for g in groups),
        startup_dma_bytes=sum(len(b[2]) for b in blobs),steady_vram_dma_bytes=0,
        scope='preloaded dot_palette scene; Mode1 BG3 + sparse BG1 patch; HDMA map switch line120',display_height=239,source_height=240)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--diagnostic',action='store_true');p.add_argument('--omit-patch',action='store_true');a=p.parse_args();build(a.out,a.diagnostic,a.omit_patch)
