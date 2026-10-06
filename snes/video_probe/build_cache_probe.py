"""Bank/generation cache experiment derived from original stream host.
SPDX-License-Identifier: MIT. No commercial input, no FPGA emulation.
"""
from pathlib import Path
import argparse,json,struct,hashlib,sys
from build_probe import Asm,planar
from build_patch_probe import encode4
from video_schedule_model import Scene,Event,reference,tile_pixel

from cache_patterns import cache_reference, cache_planar, schedule_state, pattern_audit

STATES=32

def color(c):
    # Injective 64-entry diagnostic RGB555 LUT; not a NES analog palette model.
    return (c&31)|((((c>>5)*16+(c*3)%16)&31)<<5)|(((c*7)%32)<<10)

def rgb(c):
    v=color(c);r=v&31;g=(v>>5)&31;b=(v>>10)&31
    return (((r<<3)|(r>>2))<<16)|(((g<<3)|(g>>2))<<8)|((b<<3)|(b>>2))

assert len({color(c) for c in range(64)})==64


def compile_frame(i,sprites=True,mask_selected=True):
    sprite_list=[]
    if sprites:
        sprite_list=[dict(x=24+j*7+(i%4),y=81,height=8 if j%2 else 16,tile=j,bank=j%8,behind=j%3==0) for j in range(10)]
    scene=Scene('stream_'+str(i),i,[Event(119,123,'palette',17)],sprite_list)
    exact=cache_reference(scene,i);overlay=cache_reference(Scene(scene.name,i,scene.events,[]),i);base=cache_reference(Scene(scene.name,i,scene.events,[]),i,line_only=True)
    changed=sorted({(n%256//8,n//256//8) for n,(a,b) in enumerate(zip(overlay,base)) if a!=b})
    assert len(changed)<=63,('tile capacity',i,len(changed))
    groups=[];patches=[]
    for tx,ty in changed:
        data=[overlay[(ty*8+y)*256+tx*8+x] for y in range(8) for x in range(8)];colors=set(data)
        assert len(colors)<=15,('tile colors',i,tx,ty,len(colors))
        group=next((n for n,g in enumerate(groups) if len(g|colors)<=15),None)
        if group is None:group=len(groups);groups.append(set())
        groups[group]|=colors;patches.append((tx,ty,data,group))
    assert len(groups)<=6,('palette capacity',i,len(groups))
    palette=[0]*(192 if sprites else 128)
    for j in range(16):
        palette[j]=color(j) if j%4 else 0
        palette[16+j]=color(j+17) if j%4 else 0
    lookup=[]
    for n,g in enumerate(groups):
        lookup.append({c:k+1 for k,c in enumerate(sorted(g))})
        for c,k in lookup[-1].items():palette[(n+2)*16+k]=color(c)
    data=bytearray();maps=[bytearray(64),bytearray(64)]
    for n,(tx,ty,pixels,g) in enumerate(patches,1):
        assert ty==14
        data.extend(encode4([lookup[g][c] for c in pixels]))
        for page in (0,1):struct.pack_into('<H',maps[page],tx*2,(n+64*page)|((g+2)<<10))
    packet=bytearray([0xff])*32768
    packet[:len(data)]=data;packet[0x800:0x840]=maps[0];packet[0xa00:0xa40]=maps[1]
    oam=bytearray(544);objtiles=bytearray()
    for n in range(128):oam[n*4+1]=240
    for n,sp in enumerate(sprite_list):
        for half in range(sp['height']//8):
            rowpixels=[]
            for yy in range(8):
                y=sp['y']+half*8+yy
                selected=[j for j,q in enumerate(sprite_list) if q['y']<=y<q['y']+q['height']][:8]
                tile=(sp['tile']&~1)+half if sp['height']==16 else sp['tile']
                rowpixels += [tile_pixel(sp['bank'],tile,xx,yy) if n in selected or not mask_selected else 0 for xx in range(8)]
            index=len(objtiles)//32;objtiles.extend(encode4(rowpixels))
            oam[index*4:index*4+4]=bytes([sp['x'],sp['y']+half*8,index,((sp['tile']%4)<<1)|(0 if sp['behind'] else 0x10)])
    if sprites:
        for pal in range(4):
            for c in range(1,4):palette[128+pal*16+c]=color(32+pal*4+c)
    palbytes=b''.join(struct.pack('<H',v) for v in palette)
    packet[0xc00:0xc00+len(palbytes)]=palbytes
    packet[0xe00:0xe03]=struct.pack('<HB',len(data),i)
    packet[0x1000:0x1220]=oam;packet[0x1800:0x1800+len(objtiles)]=objtiles
    stats=dict(state=i,patch_tiles=len(patches),palette_groups=len(groups),chr_bytes=len(data),map_bytes=64,cgram_bytes=len(palbytes),oam_bytes=60,obj_tiles=len(objtiles)//32,
               payload_bytes=len(data)+64+len(palbytes)+60+1024,descriptor_bytes=11,slots=2,
               cache_strategy="eight fixed 1KB pages; expected prior key; replace in admitted commit",sprite_strategy='preselected opaque rows; 8x16 split into two 8x8 OBJ' if sprites else 'none')
    expected=b''.join(rgb(c).to_bytes(3,'big') for c in exact[:256*239])
    return bytes(packet),expected,stats

class Code(Asm):
    def jump(self,n):
        # Absolute JMP/JSR remain in WRAM program bank $7e.
        self.emit(0x4c,0,0);self.fix_abs.append((len(self.data)-2,n))
    def __init__(self,base):super().__init__(base);self.fix_abs=[]
    def finish(self):
        for pos,n in self.fix_abs:struct.pack_into('<H',self.data,pos,self.labels[n]&65535)
        return super().finish()
    def load(self,addr):self.absolute(0xad,addr)
    def save(self,addr):self.absolute(0x8d,addr)


def build(out,diagnostic=False,sprites=True,fault='none'):
    out.mkdir(parents=True,exist_ok=False);rom=bytearray([0xff])*(32768*64);stats=[];audit=pattern_audit()
    for i in range(STATES):
        packet,expected,info=compile_frame(i,True,True)
        tags,old,new=schedule_state(i);window=i%8
        packet=bytearray(packet)
        # Fixed 1KB page with explicit prior and replacement physical-bank/generation keys.
        packet[0xe03:0xe0b]=bytes([window,1,old[0],old[1],new[0],new[1],0,4])
        page=b''.join(cache_planar(*new,t) for t in range(64))
        if fault=='stale' and i==8:page=b''.join(cache_planar(*old,t) for t in range(64))
        if fault=='alias':page=b''.join(cache_planar(new[0]&7,new[1],t) for t in range(64))
        if fault=='burst' and i==8:packet[0xe04]=8
        if fault=='tag' and i==8:packet[0xe06]^=1
        packet[0x2000:0x2400]=page
        info.update(window=window,prior_key=list(old),new_key=list(new),cache_tags=tags,cache_bytes=1024)
        packet=bytes(packet)
        rom[(i+1)*32768:(i+2)*32768]=packet
        (out/f'expected-{i:02}.rgb').write_bytes(expected);stats.append(info)
    # Initial CHR cache state and fixed slot maps, loaded during startup blank.
    bg=b''.join(cache_planar(bank,1,tile) for bank in range(8) for tile in range(64))
    rom[0x2000:0x4000]=bg
    for alt in (0,1):
        m=bytearray()
        for page in range(2):
            for ty in range(32):
                for lx in range(32):
                    tx=page*32+lx;pal=(tx//2+ty//2)%4+4*alt
                    m.extend(struct.pack('<H',((tx+ty)%8)*64+(tx+ty*7)%64+(pal<<10)+0x2000))
        rom[0x4000+alt*0x1000:0x5000+alt*0x1000]=m
    rom[0x6000:0x6800]=bytes(2048);
    if sprites:rom[0x6800:0x69e0]=rom[32768+0x1800:32768+0x19e0]
    rom[0x6f00:0x6f05]=bytes([120,1,119,0x11,0])
    a=Code(0x7e2000);a.emit(0x78,0xe2,0x20,0xc2,0x10)
    for r,v in [(0x2100,0x80),(0x4200,0),(0x420c,0),(0x2105,1),(0x2107,8),(0x2109,1),
                (0x210b,3),(0x210c,4),(0x2101,3),(0x212c,21 if sprites else 5),(0x212d,0),(0x2130,0),(0x2131,0),(0x2133,4),(0x2115,0x80)]:a.store(r,v)
    for r,v in [(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,3),(0x2111,0),(0x2111,0),(0x2112,255),(0x2112,3)]:a.store(r,v)
    def static_dma(src,dst,length):
        for r,v in [(0x2116,dst&255),(0x2117,dst>>8),(0x4300,1),(0x4301,0x18),(0x4302,src&255),
                    (0x4303,src>>8),(0x4304,0),(0x4305,length&255),(0x4306,length>>8),(0x420b,1)]:a.store(r,v)
    for src,dst,length in [(0xa000,0x4000,8192),(0xc000,0,4096),(0xd000,0x1000,4096),(0xe000,0x0800,2048),(0xe000,0x0c00,2048),(0xe000,0x3000,2048),(0xe000,0x3400,2048)]:static_dma(src,dst,length)
    if sprites:static_dma(0xe800,0x6000,480)
    # Unused OBJ entries/high table initialized once; only 15 active entries change.
    for r,v in [(0x2102,0),(0x2103,0),(0x4300,0),(0x4301,4),(0x4302,0),(0x4303,0x90),(0x4304,1),(0x4305,0x20),(0x4306,2),(0x420b,1)]:a.store(r,v)
    for n in range(8):a.store(0x1f60+n*2,n);a.store(0x1f61+n*2,1)
    for r,v in [(0x4310,0),(0x4311,9),(0x4312,0),(0x4313,0xef),(0x4314,0)]:a.store(r,v)
    # $1fe0 displayed frame, 1fe1 attempt, 1fe2 epoch, 1fe3 active slot,
    # 1fe4 pending slot, 1fe5 error, 1fe6 phase, 1ff0 ready.
    for r,v in [(0x1fe0,255),(0x1fe1,255),(0x1fe2,0),(0x1fe3,1),(0x1fe4,0),(0x1fe5,0),(0x1fe6,0),(0x1ff0,0)]:a.store(r,v)
    a.label('next')
    a.absolute(0xee,0x1fe1);a.load(0x1fe1);a.emit(0x29,31,0x1a,0x48,0xab);a.save(0x4304) # ROM bank for this state.
    a.load(0x1fe3);a.emit(0x49,1);a.save(0x1fe4)
    a.store(0x1fe5,0)
    a.label('wait_active');a.load(0x4212);a.branch(0x30,'wait_active')
    a.label('wait_blank');a.load(0x4212);a.branch(0x10,'wait_blank')
    a.store(0x1fe6,1);a.store(0x420c,0)
    # Admit only complete 32-byte tiles, 1..544 bytes. With sprite payload and
    # 4096 CPU/setup reserve +768 diagnostic reserve this fits the 80% budget.
    a.emit(0xc2,0x20);a.load(0x8e00);a.emit(0xc9);a.word(1);a.branch(0x90,'bad_length')
    a.emit(0xc9);a.word(545);a.branch(0xb0,'bad_length');a.emit(0x29);a.word(31);a.branch(0xd0,'bad_length')
    a.branch(0x80,'length_ok');a.label('bad_length');a.emit(0xe2,0x20);a.store(0x1fe5,0xe2);a.jump('halt')
    a.label('length_ok');a.emit(0xe2,0x20)
    # Entire descriptor admitted before any stage DMA; one page only.
    a.load(0x8e04);a.emit(0xc9,1);a.branch(0xd0,'bad_cache')
    a.load(0x8e03);a.emit(0xc9,8);a.branch(0xb0,'bad_cache')
    a.load(0x8e09);a.branch(0xd0,'bad_cache')
    a.load(0x8e0a);a.emit(0xc9,4);a.branch(0xd0,'bad_cache')
    a.load(0x8e07);a.emit(0xc9,16);a.branch(0xb0,'bad_cache')
    a.load(0x8e08);a.emit(0xc9,2);a.branch(0xb0,'bad_cache')
    a.branch(0x80,'cache_shape_ok');a.label('bad_cache');a.store(0x1fe5,0xe3);a.jump('halt')
    a.label('cache_shape_ok')
    a.emit(0xc2,0x20);a.load(0x8e03);a.emit(0x29);a.word(255);a.emit(0x0a,0xaa)
    a.absolute(0xbd,0x1f60);a.absolute(0xcd,0x8e05);a.branch(0xf0,'tags_ok')
    a.emit(0xe2,0x20);a.store(0x1fe5,0xe4);a.jump('halt')
    a.label('tags_ok');a.emit(0xe2,0x20)
    if diagnostic:
        # Deliberate per-frame diagnostic cost without PPU state changes.
        for j in range(16):a.store(0x1f80+j,j)
    # Stage CHR into non-visible slot. All values are known before DMA starts.
    a.store(0x2116,0x10);a.load(0x1fe4);a.emit(0x0a,0x0a,0x09,0x30);a.save(0x2117)
    for r,v in [(0x4300,1),(0x4301,0x18),(0x4302,0),(0x4303,0x80)]:a.store(r,v)
    a.load(0x8e00);a.save(0x4305);a.load(0x8e01);a.save(0x4306)
    a.store(0x420b,1)
    # Only patch row 14 is dirty; OBJ uses its independent OAM entries.
    a.store(0x2116,0xc0);a.load(0x1fe4);a.emit(0x0a,0x0a,0x09,9);a.save(0x2117)
    a.store(0x4302,0);a.load(0x1fe4);a.emit(0x0a,0x09,0x88);a.save(0x4303)
    a.store(0x4305,0x40);a.store(0x4306,0);a.store(0x420b,1);a.store(0x1fe6,2)
    if fault=='reset':
        a.load(0x1fe2);a.branch(0xd0,'no_reset');a.load(0x1fe1);a.emit(0xc9,7);a.branch(0xd0,'no_reset')
        a.absolute(0xee,0x1fe2);a.store(0x1fe5,0x52);a.store(0x1fe6,4);a.store(0x420c,2);a.absolute(0xce,0x1fe1);a.jump('next')
        a.label('no_reset')
    # Cooperative producer reset can cancel before this point only. Palette commit is
    # bounded/noninterruptible; reset requests during it must be deferred in real hardware.
    a.load(0x4212);a.branch(0x30,'commit_allowed');a.store(0x1fe5,0xe1);a.jump('halt')
    a.label('commit_allowed');a.store(0x1fe6,5)
    # Destructive cache replacement is only inside this bounded VBlank commit.
    a.store(0x2116,0);a.load(0x8e03);a.emit(0x0a,0x09,0x40);a.save(0x2117)
    for r,v in [(0x4300,1),(0x4301,0x18),(0x4302,0),(0x4303,0xa0),(0x4305,0),(0x4306,4),(0x420b,1)]:a.store(r,v)
    a.emit(0xc2,0x20);a.load(0x8e07);a.absolute(0x9d,0x1f60);a.emit(0xe2,0x20)
    a.store(0x2121,0)
    for r,v in [(0x4300,2),(0x4301,0x22),(0x4302,0),(0x4303,0x8c),(0x4305,0x80 if sprites else 0),(0x4306,1),(0x420b,1)]:a.store(r,v)
    if sprites:
        for r,v in [(0x2102,0),(0x2103,0),(0x4300,0),(0x4301,4),(0x4302,0),(0x4303,0x90),(0x4305,60),(0x4306,0),(0x420b,1)]:a.store(r,v)
    a.load(0x8e02);a.save(0x2111);a.store(0x2111,0)
    a.load(0x1fe4);a.emit(0x0a,0x0a,0x09,8);a.save(0x2107)
    a.load(0x1fe4);a.save(0x1fe3);a.load(0x1fe1);a.save(0x1fe0)
    a.store(0x420c,2);a.store(0x2100,15);a.store(0x1ff0,0xa5);a.store(0x1fe6,3)
    a.jump('next');a.label('halt');a.store(0x420c,2);a.store(0x1fe6,0xee);a.label('stopped');a.branch(0x80,'stopped')
    body=a.finish();assert len(body)<4096;rom[0x1000:0x1000+len(body)]=body
    boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
    boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
    boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
    code=boot.finish();rom[:len(code)]=code
    rom[0x7fc0:0x7fd5]=b'NES P1 STREAM TEST   '.ljust(21,b' ')[:21]
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,11,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for p in range(0x7fe0,0x8000,2):rom[p:p+2]=struct.pack('<H',0x8000)
    checksum=sum(rom)&65535;rom[0x7fdc:0x7fe0]=struct.pack('<HH',checksum^65535,checksum)
    (out/'stream.sfc').write_bytes(rom)
    sources=[Path(__file__),Path(__file__).with_name('cache_patterns.py'),Path(__file__).with_name('build_probe.py'),Path(__file__).with_name('build_patch_probe.py'),Path(__file__).resolve().parents[2]/'tools/video_schedule_model.py']
    manifest=dict(candidate='NES-P1-CACHE-003',pattern_audit=audit,state_count=STATES,diagnostic=diagnostic,sprites=sprites,fault=fault,states=stats,
       rom_sha256=hashlib.sha256(rom).hexdigest(),source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
       admission=dict(max_patch_bytes=544,max_cache_bytes=1024,max_cache_pages=1,alignment_bytes=32,cpu_setup_reserve=4096,diagnostic_reserve=768,projected_worst_clocks=2076*8+4096+768,usable_blank_clocks=29124),
       max_payload_bytes=max(s['payload_bytes'] for s in stats),startup_dma_bytes=24576+480+544,body_bytes=len(body),
       scope='ROM-supplied synthetic frames, real SNES WRAM/VRAM/CGRAM/HDMA; no FPGA/MCU/external SRAM timing')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('source_hashes','states')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--diagnostic',action='store_true');p.add_argument('--fault',choices=['none','reset','burst','tag','stale','alias'],default='none');a=p.parse_args();build(a.out,a.diagnostic,True,a.fault)
