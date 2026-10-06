# Fine-X packet with a separate right map column. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json,struct
from build_nes_trace_replay import Asm,Code,convert,palette,display_rgb
from verify_nes_video_workloads import read_case
from verify_nes_rtl_fetch import RGB,PALETTE
CANDIDATE='NES-R2-FINE-SCROLL-022'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fine_coord(line,dot):
    if line>=0 and dot<=247:return line,dot//8+2
    if line<239 and dot>=321:return line+1,(dot-321)//8
    return None
def encode(frame,seq,features,chrdata):
    assert features['ppu_mask']==10 and features['ppu_ctrl']==136
    assert not features['active_ppu_writes'] and not features['scroll_y']
    assert features['immutable_chr_rom'] and len(chrdata)==16384
    fine=features['scroll_x'];assert 0<=fine<8
    cells={};planes=set();release=0
    for e in seq:
        pos=fine_coord(e['line'],e['dot'])
        if pos is None:continue
        y,x=pos;key=(y//8,x);plane=e['offset']%16//8
        assert 0<=x<=32 and 0<=y<240
        assert cells.get(key,e['tile'])==e['tile'],'in-cell tile change'
        assert e['offset']%8==y%8 and e['tile']==e['offset']//16
        assert 0<=e['offset']<len(chrdata) and chrdata[e['offset']]==e['value']
        assert (y,x,plane) not in planes
        cells[key]=e['tile'];planes.add((y,x,plane));release=e['tick']
    assert len(cells)==990 and len(planes)==15840,'missing map or edge plane'
    main=b''.join(struct.pack('<H',cells[y,x]) for y in range(30) for x in range(32))
    edge=b''.join(struct.pack('<H',cells[y,32]) for y in range(30))
    return struct.pack('<4sBBBBHHII',b'NFX1',1,frame,fine,0,256,240,release,1980)+main+edge+palette()
def decode(p,atlas):
    magic,version,frame,fine,flags,w,h,release,n=struct.unpack('<4sBBBBHHII',p[:20])
    assert (magic,version,flags,w,h,n,len(p))==(b'NFX1',1,0,256,240,1980,2008)
    assert 0<=fine<8 and p[-8:]==palette() and len(atlas)==16384
    main=[v[0] for v in struct.iter_unpack('<H',p[20:1940])]
    edge=[v[0] for v in struct.iter_unpack('<H',p[1940:2000])]
    assert all(t<1024 for t in main+edge)
    result=bytearray()
    for y in range(240):
        for x in range(256):
            u=x+fine;col=u//8;tile=edge[y//8] if col==32 else main[y//8*32+col]
            lo,hi=atlas[tile*16+(y%8)*2:tile*16+(y%8)*2+2];bit=7-u%8
            result.append(PALETTE[(lo>>bit&1)|((hi>>bit&1)<<1)])
    return bytes(result)
def build(a):
    assert not a.out.exists()
    frames,bg,_,_,chrdata=read_case(a.workloads,a.case)
    atlas=convert(chrdata);lut=display_rgb();inverse={v:k for k,v in RGB.items()}
    packets=[];expected=[];stats=[]
    for i,info in enumerate(frames,1):
        seq=[e for e in bg if e['frame']==info['frame']]
        p=encode(i,seq,info['features'],chrdata)
        rgb=(a.workloads/a.case/'capture'/f"frame-{info['frame']:03}.rgb").read_bytes()
        golden=bytes(inverse[rgb[j:j+3]] for j in range(0,len(rgb),3))
        assert decode(p,atlas)==golden
        packets.append(p);expected.append(golden)
        stats.append(dict(frame=i,source_frame=info['frame'],fine_x=info['features']['scroll_x'],
                     release_tick=struct.unpack_from('<I',p,12)[0],packet_bytes=2008,ppu_dma_bytes=1988))
    a.out.mkdir(parents=True)
    for i,(p,golden) in enumerate(zip(packets,expected),1):
        (a.out/f'packet-{i}.bin').write_bytes(p)
        (a.out/f'expected-{i}.idx').write_bytes(golden)
        (a.out/f'expected-{i}.rgb').write_bytes(b''.join(lut[c] for c in golden[a.viewport*256:(a.viewport+239)*256]))
    (a.out/'chr-snes.bin').write_bytes(atlas)
    rom=bytearray([255])*65536;rom[0x2000:0x6000]=atlas
    for i,p in enumerate(packets):
        supplied=bytearray(p)
        if a.fault=='edge':
            for y in range(30):supplied[1940+y*2]^=1
        if a.fault=='length' and i==1:supplied[16]=0
        rom[0x8000+i*2048:0x8000+i*2048+len(p)]=supplied
    c=Code(0x7e2000);c.emit(0x78,0xe2,0x20,0xc2,0x10)
    for r,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2105,0),(0x2107,1),(0x210b,2),
                (0x212c,1),(0x212d,0),(0x2130,0),(0x2131,0),(0x2133,4),
                (0x1ff0,0),(0x1fe0,0),(0x1fe5,0),(0x1fe6,0)]:c.store(r,v)
    y=(a.viewport-1)&1023
    for r,v in [(0x210d,0),(0x210d,0),(0x210e,y&255),(0x210e,y>>8)]:c.store(r,v)
    def dma(bank,src,dst,n,pal=False,column=False):
        if pal:c.store(0x2121,0)
        else:
            c.store(0x2115,0x81 if column else 0x80)
            c.store(0x2116,dst&255);c.store(0x2117,dst>>8)
        for r,v in [(0x4300,2 if pal else 1),(0x4301,0x22 if pal else 0x18),
                    (0x4302,src&255),(0x4303,src>>8),(0x4304,bank),
                    (0x4305,n&255),(0x4306,n>>8),(0x420b,1)]:c.store(r,v)
    dma(0,0xa000,0x2000,16384)
    c.label('settle_active');c.absolute(0xad,0x4212);c.branch(0x30,'settle_active')
    c.label('settle_blank');c.absolute(0xad,0x4212);c.branch(0x10,'settle_blank')
    for i in range(4):
        f=i+1;addr=0x8000+i*2048;slot=i%2
        c.store(0x1fe1,f)
        c.label(f'active{f}');c.absolute(0xad,0x4212);c.branch(0x30,f'active{f}')
        c.label(f'blank{f}');c.absolute(0xad,0x4212);c.branch(0x10,f'blank{f}')
        c.store(0x1fe6,1)
        for j in list(range(12))+list(range(16,20)):
            c.long(0xaf,0x010000+addr+j);c.emit(0xc9,packets[i][j]);c.branch(0xf0,f'ok{f}_{j}');c.jump('reject');c.label(f'ok{f}_{j}')
        dma(1,addr+20,slot*0x800,1920)
        dma(1,addr+1940,slot*0x800+0x400,60,column=True)
        dma(1,addr+2000,0,8,True)
        c.long(0xaf,0x010000+addr+6)
        if a.fault=='scroll':c.emit(0xa9,0)
        c.absolute(0x8d,0x210d);c.store(0x210d,0)
        c.store(0x2107,slot*8+1)
        c.store(0x1fe0,f);c.store(0x2100,15);c.store(0x1ff0,165);c.store(0x1fe6,3)
    c.jump('stopped');c.label('reject');c.store(0x1fe5,226);c.store(0x1fe6,238)
    c.label('stopped');c.branch(0x80,'stopped')
    body=c.finish();assert len(body)<4096;rom[0x1000:0x1000+len(body)]=body
    boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
    boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
    boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
    rom[:len(boot.finish())]=boot.finish()
    rom[0x7fc0:0x7fd5]=b'NES FINE SCROLL022'.ljust(21,b' ')
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,6,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    assert len(rom)==65536 and rom[0x8000:0x8004]==b'NFX1'
    (a.out/'replay.sfc').write_bytes(rom)
    m=dict(candidate=CANDIDATE,case=a.case,viewport=a.viewport,fault=a.fault,frames=stats,
           rom_sha256=sha(a.out/'replay.sfc'),builder_sha256=sha(__file__),
           input_trace_sha256=sha(a.workloads/a.case/'capture/trace.tsv'),
           input_rom_sha256=sha(a.workloads/a.case/'build/mmc3.nes'),
           packet_bytes=2008,packet_stride=2048,ppu_dma_bytes=1988,startup_chr_bytes=16384,
           map_width_tiles=64,transmitted_columns=33,source_height=240,display_height=239,
           live_producer_deadline_proven=False,product_display_policy_approved=False,
           scope='Offline ROM-fed fine-X0/1 reference replay;33captured tile columns,full16KiB immutable CHR preload. No coarse/vertical/mid-frame scroll or sprite support.')
    (a.out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidate=CANDIDATE,case=a.case,viewport=a.viewport,fault=a.fault,body_bytes=len(body),packet_bytes=2008),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workloads',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--case',choices=['baseline','fine_x'],default='fine_x')
    p.add_argument('--viewport',type=int,choices=[0,1],default=0)
    p.add_argument('--fault',choices=['none','edge','scroll','length'],default='none')
    build(p.parse_args())