# Actual NES fetch -> bounded SNES BG packet/replay fixture. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_nes_fetch_workload import events
from verify_nes_mmc3_integrated import numbers,verify
from verify_nes_rtl_fetch import PALETTE,RGB
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'snes/video_probe'))
from build_probe import Asm
CANDIDATE='NES-R2-TRACE-REPLAY-020'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def convert(data):
    assert len(data)%16==0
    return bytes(v for start in range(0,len(data),16) for y in range(8) for v in (data[start+y],data[start+y+8]))
def palette():
    vals=[]
    for c in PALETTE:
        rgb=RGB[c]
        q=[(v*31+127)//255 for v in rgb]
        vals.append(q[0]|q[1]<<5|q[2]<<10)
    assert len(set(vals))==4
    return struct.pack('<4H',*vals)
def display_rgb():
    out=[]
    for v in struct.unpack('<4H',palette()):
        q=[v&31,(v>>5)&31,(v>>10)&31]
        out.append(bytes((c<<3)|(c>>2) for c in q))
    return dict(zip(PALETTE,out))
def packet(frame,seq):
    cells={};release=0;planes=set()
    for e in seq:
        if e['pixel'] is None:continue
        y,x=e['pixel'];key=(y//8,x)
        assert cells.get(key,e['tile'])==e['tile'],'tile changes inside an8x8cell unsupported'
        assert e['offset']%8==y%8,'nonzero/fine scroll unsupported'
        cells[key]=e['tile'];release=e['tick']
        pos=(y,x,(e['offset']%16)//8)
        assert pos not in planes
        planes.add(pos)
    assert len(cells)==960 and len(planes)==15360,'incomplete240row source frame'
    tilemap=b''.join(struct.pack('<H',cells[y,x]) for y in range(30) for x in range(32))
    header=struct.pack('<4sBBHHHI',b'NTR0',1,frame,256,240,len(tilemap),release)
    return header+tilemap+palette(),release
def decode(p,atlas):
    magic,version,f,w,h,n,release=struct.unpack('<4sBBHHHI',p[:16])
    assert (magic,version,w,h,n,len(p))==(b'NTR0',1,256,240,1920,1944)
    assert p[-8:]==palette()
    result=bytearray(256*240)
    for cell,(tile,) in enumerate(struct.iter_unpack('<H',p[16:1936])):
        assert tile<1024 and tile*16+16<=len(atlas)
        for y in range(8):
            lo,hi=atlas[tile*16+y*2:tile*16+y*2+2]
            for x in range(8):
                result[(cell//32*8+y)*256+(cell%32*8+x)]=PALETTE[((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)]
    return bytes(result)
class Code(Asm):
    def __init__(self,base):super().__init__(base);self.jumps=[]
    def jump(self,label):self.emit(0x4c,0,0);self.jumps.append((len(self.data)-2,label))
    def finish(self):
        for p,label in self.jumps:struct.pack_into('<H',self.data,p,self.labels[label]&65535)
        return super().finish()
def build(a):
    assert not a.out.exists()
    checked=verify(a.run,a.reference,a.rom);assert checked['passed']
    chrdata=bytes(int(v,16) for v in (a.run/'chr.hex').read_text().split())
    assert len(chrdata)==16384
    trace=events(numbers(a.run/'fetch.tsv'),chrdata)
    packets=[];frames=[];expected=[]
    atlas=convert(chrdata);lut=display_rgb()
    for f in range(1,5):
        p,release=packet(f,[e for e in trace if e['frame']==f])
        golden=bytes(int(v,16) for v in (a.run/f'frame-{f:3}.hex').read_text().split())
        assert decode(p,atlas)==golden
        expected.append(golden);packets.append(p)
        frames.append(dict(frame=f,release_nes_master_tick=release,packet_bytes=len(p),
                           map_bytes=1920,cgram_bytes=8,ppu_dma_bytes=1928,source_pixels=len(golden),
                           indexed_sha256=hashlib.sha256(golden).hexdigest()))
    a.out.mkdir(parents=True)
    for f,(p,golden) in enumerate(zip(packets,expected),1):
        (a.out/f'packet-{f}.bin').write_bytes(p)
        (a.out/f'expected-{f}.idx').write_bytes(golden)
        viewport=golden[a.viewport*256:(a.viewport+239)*256]
        (a.out/f'expected-{f}.rgb').write_bytes(b''.join(lut[c] for c in viewport))
    (a.out/'chr-snes.bin').write_bytes(atlas)
    rom=bytearray([255])*65536
    supplied=bytearray(atlas)
    if a.fault=='chr':
        supplied[2*16]^=1
    rom[0x2000:0x6000]=supplied
    for i,p in enumerate(packets):
        altered=bytearray(p)
        if a.fault=='length' and i==1:altered[10]=0
        rom[0x8000+i*2048:0x8000+i*2048+len(p)]=altered
    c=Code(0x7e2000);c.emit(0x78,0xe2,0x20,0xc2,0x10)
    for r,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2105,0),(0x2107,0),(0x210b,2),
                (0x212c,1),(0x212d,0),(0x2130,0),(0x2131,0),(0x2133,4),(0x2115,128),
                (0x1ff0,0),(0x1fe0,0),(0x1fe5,0),(0x1fe6,0)]:
        c.store(r,v)
    y=(a.viewport-1)&1023
    for r,v in [(0x210d,0),(0x210d,0),(0x210e,y&255),(0x210e,y>>8)]:c.store(r,v)
    def dma(bank,src,dst,n,pal=False):
        if pal:c.store(0x2121,0)
        else:c.store(0x2116,dst&255);c.store(0x2117,dst>>8)
        for r,v in [(0x4300,2 if pal else 1),(0x4301,0x22 if pal else 0x18),
                    (0x4302,src&255),(0x4303,src>>8),(0x4304,bank),
                    (0x4305,n&255),(0x4306,n>>8),(0x420b,1)]:c.store(r,v)
    dma(0,0xa000,0x2000,16384)
    # Allow overscan timing to latch during startup; normal frames remain consecutive.
    c.label('settle_active');c.absolute(0xad,0x4212);c.branch(0x30,'settle_active')
    c.label('settle_blank');c.absolute(0xad,0x4212);c.branch(0x10,'settle_blank')
    for i in range(4):
        f=i+1;addr=0x8000+i*2048;slot=i%2
        c.store(0x1fe1,f)
        c.label(f'active{f}');c.absolute(0xad,0x4212);c.branch(0x30,f'active{f}')
        c.label(f'blank{f}');c.absolute(0xad,0x4212);c.branch(0x10,f'blank{f}')
        c.store(0x1fe6,1)
        # This static ROM transport fixture admits only the current complete packet.
        # Producer release/clock synchronization is NOT supplied by the emulator.
        for j,v in enumerate(packets[i][:12]):
            c.long(0xaf,0x010000+addr+j);c.emit(0xc9,v);c.branch(0xf0,f'ok{f}_{j}');c.jump('reject');c.label(f'ok{f}_{j}')
        dma(1,addr+16,slot*0x400,1920)
        dma(1,addr+1936,0,8,True)
        c.store(0x2107,slot*4)
        c.store(0x1fe0,f);c.store(0x2100,15);c.store(0x1ff0,165);c.store(0x1fe6,3)
    c.jump('stopped')
    c.label('reject');c.store(0x1fe5,226);c.store(0x1fe6,238)
    c.label('stopped');c.branch(0x80,'stopped')
    body=c.finish();assert len(body)<4096;rom[0x1000:0x1000+len(body)]=body
    boot=Asm(0x8000)
    boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
    boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
    boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
    rom[:len(boot.finish())]=boot.finish()
    rom[0x7fc0:0x7fd5]=b'NES TRACE REPLAY020'.ljust(21,b' ')
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,6,0,1,0,0])
    rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for offset in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,offset,0x8000)
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    assert len(rom)==65536 and rom[0x8000:0x8004]==b'NTR0', 'LoROM layout shifted'
    (a.out/'replay.sfc').write_bytes(rom)
    result=dict(candidate=CANDIDATE,frames=frames,viewport=a.viewport,fault=a.fault,
                rom_sha256=sha(a.out/'replay.sfc'),source_trace_sha256=sha(a.run/'fetch.tsv'),
                source_chr_sha256=sha(a.run/'chr.hex'),builder_sha256=sha(__file__),
                source_height=240,display_height=239,product_display_policy_approved=False,
                startup_chr_dma_bytes=16384,packet_slot_bytes=2048,serialized_packet_bytes=1944,
                whole_immutable_rom_preload=True,observed_future_union_preload=False,
                palette=dict(kind='RGB555 nearest quantization of four pinned Mesen RGB colors; four distinct symbols preserved',
                             source={str(c):RGB[c].hex() for c in PALETTE},display={str(c):lut[c].hex() for c in PALETTE}),
                producer_clock_connected=False,live_nes_to_snes=False,
                scope='Archived actual BG trace converted to packets; immutable full16KiB CHR startup; offline SNES ROM supplier; no producer release/CDC timing proof.')
    (a.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidate=CANDIDATE,viewport=a.viewport,fault=a.fault,packet_bytes=1944,body_bytes=len(body)),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('run','reference','rom','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--viewport',type=int,choices=[0,1],default=0)
    p.add_argument('--fault',choices=['none','chr','length'],default='none')
    build(p.parse_args())