"""Build an original SNES WRAM+HDMA fixed-event probe. SPDX-License-Identifier: MIT."""
from pathlib import Path
import sys,argparse,hashlib,json,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from video_schedule_model import planar,scenes,reference

class Asm:
    def __init__(self,base):self.base=base;self.data=bytearray();self.labels={};self.fix=[]
    def emit(self,*v):self.data.extend(v)
    def word(self,v):self.data.extend(struct.pack('<H',v))
    def absolute(self,op,addr):self.emit(op);self.word(addr)
    def long(self,op,addr):self.emit(op,addr&255,(addr>>8)&255,addr>>16)
    def label(self,n):self.labels[n]=self.base+len(self.data)
    def branch(self,op,n):self.emit(op,0);self.fix.append((len(self.data)-1,n))
    def store(self,addr,v):self.emit(0xa9,v);self.absolute(0x8d,addr)
    def finish(self):
        for p,n in self.fix:
            d=self.labels[n]-(self.base+p+1)
            assert -128<=d<=127
            self.data[p]=d&255
        return bytes(self.data)

def color(c):
    if c==0:return 0
    return ((c*2)&31)|(((c*5)&31)<<5)|(((c*7)&31)<<10)

def rgb(c):
    v=color(c);r=v&31;g=(v>>5)&31;b=(v>>10)&31
    return (((r<<3)|(r>>2))<<16)|(((g<<3)|(g>>2))<<8)|((b<<3)|(b>>2))

def build(out,diagnostic=False,fault_split=False):
    out.mkdir(parents=True,exist_ok=False)
    rom=bytearray([0xff])*32768
    # Graphics at ROM $a000; generated from the same physical atlas contract as B.
    tiles=b''.join(planar(bank,tile,0) for bank in range(8) for tile in range(64))
    tilemap=bytearray()
    for page in range(2):
        for ty in range(32):
            for lx in range(32):
                tx=page*32+lx;bank=(tx+ty)%8;tile=(tx+ty*7)%64;pal=(tx//2+ty//2)%4
                tilemap.extend(struct.pack('<H',bank*64+tile+(pal<<10)))
    palette=b''.join(struct.pack('<H',color(i)) for i in range(16))
    rom[0x2000:0x4000]=tiles;rom[0x4000:0x5000]=tilemap;rom[0x5000:0x5020]=palette
    # Direct HDMA mode 2 writes BG1HOFS twice at the start of each segment.
    # First entry covers 117 displayed rows, then x=0 for 122 rows.
    rom[0x5100:0x5107]=bytes([116 if fault_split else 117,1,0,123 if fault_split else 122,0,0,0])
    a=Asm(0x7e2000);a.emit(0x78,0xe2,0x20,0xc2,0x10)
    for reg,val in [(0x2100,0x80),(0x4200,0),(0x420c,0),(0x2105,0),(0x2107,1),(0x210b,2),
                    (0x212c,1),(0x212d,0),(0x2130,0),(0x2131,0),(0x2133,4),(0x2115,0x80)]:a.store(reg,val)
    for reg,val in [(0x210d,1),(0x210d,0),(0x210e,255),(0x210e,3)]:a.store(reg,val)
    def dma(src,dst,size,target=0x18,mode=1):
        if target==0x18:
            a.store(0x2116,dst&255);a.store(0x2117,dst>>8)
        else:a.store(0x2121,0)
        for r,v in [(0x4300,mode),(0x4301,target),(0x4302,src&255),(0x4303,src>>8),(0x4304,0),
                    (0x4305,size&255),(0x4306,size>>8),(0x420b,1)]:a.store(r,v)
    dma(0xa000,0x2000,len(tiles));dma(0xc000,0,len(tilemap));dma(0xd000,0,len(palette),0x22,2)
    for r,v in [(0x4310,2),(0x4311,0x0d),(0x4312,0),(0x4313,0xd1),(0x4314,0)]:a.store(r,v)
    # Exit initial loading blank only during VBlank; no repeated forced blank.
    a.label('wait_active');a.absolute(0xad,0x4212);a.branch(0x30,'wait_active')
    a.label('wait_blank');a.absolute(0xad,0x4212);a.branch(0x10,'wait_blank')
    a.store(0x420c,2);a.store(0x2100,15)
    a.store(0x1ff0,0xa5)
    if diagnostic:a.store(0x1ff1,0xd1)
    a.label('loop');a.branch(0x80,'loop')
    body=a.finish();assert len(body)<4096;rom[0x1000:0x1000+len(body)]=body
    boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a)
    # DBR=0, DP=0; native registers known. A 16bit, X/Y 16bit for MVN.
    boot.emit(0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
    boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
    boot.emit(0x54,0x7e,0x00) # MVN source 00, destination 7e; DBR becomes 7e.
    boot.emit(0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
    code=boot.finish();rom[:len(code)]=code
    rom[0x7fc0:0x7fd5]=b'NES P1 WRAM HDMA TEST '.ljust(21,b' ')[:21]
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
    rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for p in range(0x7fe0,0x8000,2):rom[p:p+2]=struct.pack('<H',0x8000)
    checksum=sum(rom)&0xffff;rom[0x7fdc:0x7fe0]=struct.pack('<HH',checksum^0xffff,checksum)
    (out/'probe.sfc').write_bytes(rom)
    scene=next(s for s in scenes() if s.name=='scroll_split_1')
    pixels=reference(scene)
    (out/'expected.json').write_text(json.dumps(dict(width=256,height=240,pixels=pixels,lut=[rgb(c) for c in range(64)])))
    manifest=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),model_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'tools/video_schedule_model.py').read_bytes()).hexdigest(),candidate='NES-P1-WRAM-001',diagnostic=diagnostic,fault_split=fault_split,rom_sha256=hashlib.sha256(rom).hexdigest(),
                  startup_dma_bytes=len(tiles)+len(tilemap)+len(palette),steady_vram_dma_bytes=0,
                  hdma_channels=1,hdma_payload_bytes=4,display_height=239,source_height=240,
                  missing_source_row=239,product_display_policy_approved=False,body_bytes=len(body),
                  scope='fixed scroll=1, split y=117; preloaded CHR/map; no sprites/palette events or FPGA')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--diagnostic',action='store_true');p.add_argument('--fault-split',action='store_true');a=p.parse_args();build(a.out,a.diagnostic,a.fault_split)
