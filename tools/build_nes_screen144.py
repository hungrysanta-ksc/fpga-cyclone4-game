# SPDX-License-Identifier: MIT
"""Live NCR1 SNES client. Complete packet via044 MMIO -> WRAM -> SNES PPU."""
from pathlib import Path
import argparse, hashlib, json, struct
from build_nes_trace_replay import Asm, Code, convert

def build(chr_data, out):
    assert len(chr_data)==16384 and not out.exists()
    out.mkdir(parents=True)
    c=Code(0x7e2000);c.emit(0x78,0xe2,0x20,0xc2,0x10);c.store(0x7000,2)
    for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2101,0),(0x2105,0),(0x2106,0),
                (0x2107,1),(0x2108,0),(0x2109,0),(0x210a,0),(0x210b,2),(0x210c,0),
                (0x212c,1),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),
                (0x2132,224),(0x2133,4),(0x1ff0,0),(0x1fe0,0),(0x1fe8,0),(0x1fd0,1),(0x1fd1,0)]:c.store(a,v)
    for a in range(0x2123,0x212c):c.store(a,0)
    for a,v in [(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,3)]:c.store(a,v)
    def dma(bank,src,dst,n,kind='vram'):
        if kind=='palette':c.store(0x2121,0)
        elif kind=='wram':
            for a,v in [(0x2181,dst&255),(0x2182,dst>>8),(0x2183,0)]:c.store(a,v)
        else:
            c.store(0x2115,0x81 if kind=='column' else 0x80)
            c.store(0x2116,dst&255);c.store(0x2117,dst>>8)
        mode,port=(0,0x80) if kind=='wram' else (2,0x22) if kind=='palette' else (1,0x18)
        for a,v in [(0x4300,mode),(0x4301,port),(0x4302,src&255),(0x4303,src>>8),
                    (0x4304,bank),(0x4305,n&255),(0x4306,n>>8),(0x420b,1)]:c.store(a,v)
    def blank(label):
        c.label(label+'a');c.absolute(0xad,0x4212);c.branch(0x30,label+'a')
        c.label(label+'b');c.absolute(0xad,0x4212);c.branch(0x10,label+'b')
    def require(a,v,label,error,long=False):
        (c.long if long else c.absolute)(0xaf if long else 0xad,a)
        c.emit(0xc9,v);c.branch(0xf0,label);c.store(0x1fe8,error);c.jump('error');c.label(label)
    def hold(label,stage):
        c.store(0x7000,stage);c.store(0x1fd8,stage)
        c.emit(0xa2,180,0);c.label(label)
        blank(label+'v');c.emit(0xca);c.branch(0xd0,label)
    # Load the144 readable atlas, then immediately consume actual NES packets.
    dma(1,0x8000,0x2000,16384)
    # Blue backdrop while awaiting a first packet; no uninitialized tiles shown.
    c.store(0x212c,0);c.store(0x2121,0);c.store(0x2122,0);c.store(0x2122,0x7c)
    c.store(0x2100,15);c.store(0x7000,0x34);c.store(0x1fd8,0x34)
    c.label('next')
    c.absolute(0xad,0x600b);c.absolute(0x8d,0x6002)
    c.absolute(0xad,0x600c);c.absolute(0x8d,0x6003)
    for a,b in [(0x1fd0,0x6004),(0x1fd1,0x6005)]:c.absolute(0xad,a);c.absolute(0x8d,b)
    c.emit(0xa2,255,255)
    c.label('acquire');c.store(0x6000,1)
    c.label('poll');c.absolute(0xad,0x6000);c.emit(0x89,4);c.branch(0xf0,'notfault')
    c.store(0x1fe8,4);c.jump('error');c.label('notfault');c.emit(0x89,1);c.branch(0xd0,'got')
    c.emit(0xca);c.branch(0xd0,'budget');c.store(0x1fe8,1);c.jump('error')
    c.label('budget');c.emit(0x89,2);c.branch(0xd0,'poll');c.jump('acquire')
    c.label('got')
    for a,v,n in [(0x6006,0xd8,'lenlo'),(0x6007,7,'lenhi'),(0x6001,0,'stage'),(0x600a,0,'front')]:require(a,v,n,2)
    dma(0x40,0x8000,0x4000,2008,'wram');c.store(0x7000,4)
    for a,v,n in [(0x6008,0xd8,'readlo'),(0x6009,7,'readhi'),(0x6001,0,'stage2'),(0x600a,0,'front2')]:require(a,v,n,3)
    fixed={0:78,1:67,2:82,3:49,4:1,7:0,8:0,9:1,10:240,11:0,16:188,17:7,18:0,19:0}
    for a,v in fixed.items():require(0x7e4000+a,v,'header'+str(a),7,True)
    c.long(0xaf,0x7e4006);c.emit(0xc9,8);c.branch(0x90,'fineok');c.store(0x1fe8,7);c.jump('error');c.label('fineok')
    c.long(0xaf,0x7e4005);c.emit(0x3a,0xc9,4);c.branch(0x90,'idok');c.store(0x1fe8,7);c.jump('error');c.label('idok')
    # The packet is now in WRAM; release the FPGA slot before waiting for vblank.
    c.store(0x6000,2);c.emit(0xa2,255,255)
    c.label('commitwait');c.absolute(0xad,0x6000);c.branch(0xf0,'committed')
    c.emit(0x89,4);c.branch(0xd0,'commitfail');c.emit(0xca);c.branch(0xd0,'commitwait')
    c.label('commitfail');c.store(0x1fe8,5);c.jump('error');c.label('committed')
    c.store(0x7000,5);blank('transfer');c.store(0x2100,128);c.store(0x1fe6,1)
    dma(0x7e,0x4014,0,1920);dma(0x7e,0x4794,0x400,60,'column');dma(0x7e,0x47d0,0,8,'palette')
    c.long(0xaf,0x7e4006);c.absolute(0x8d,0x210d);c.store(0x210d,0)
    c.long(0xaf,0x7e4005);c.absolute(0x8d,0x1fe0)
    c.store(0x212c,1);c.store(0x2100,15);c.store(0x1ff0,165);c.store(0x1fe6,3);c.store(0x7000,6);c.store(0x7000,0x63)
    c.emit(0xc2,0x20);c.absolute(0xad,0x1fd0);c.emit(0x1a);c.absolute(0x8d,0x1fd0)
    c.emit(0xe2,0x20);c.branch(0xd0,'again');c.store(0x1fe8,6);c.jump('error')
    c.label('again');c.jump('next')
    c.label('error');c.absolute(0xad,0x1fe8);c.absolute(0x8d,0x7001);c.store(0x7000,255)
    c.store(0x2100,128);c.store(0x212c,0);c.store(0x2121,0);c.store(0x2122,31);c.store(0x2122,0)
    c.store(0x2100,15);c.store(0x1fe6,255);c.store(0x1ff0,165)
    c.label('stopped');c.jump('stopped')
    body=c.finish();assert len(body)<0xfc0
    rom=bytearray([255])*65536;rom[0x1000:0x1000+len(body)]=body
    rom[0x8000:0xc000]=convert(chr_data)
    boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
    boot.emit(0xe2,0x20,0xa9,128,0x8d,0,0x21,0xa9,0,0x8d,0,0x42,0x8d,0x0c,0x42,0xa9,1,0x8d,0,0x70,0xc2,0x20)
    boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
    boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
    rom[:len(boot.finish())]=boot.finish();rom[0x7fc0:0x7fd5]=b'NES LIVE SCREEN144'.ljust(21,b' ')
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,6,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    compact=rom[:0x2000]+rom[0x8000:0xc000];compact[0x1fc0:0x2000]=rom[0x7fc0:0x8000]
    (out/'screen144.sfc').write_bytes(rom)
    (out/'screen-program.hex').write_text(''.join(f'{b:02x}\n' for b in compact))
    (out/'result.json').write_text(json.dumps(dict(candidate='NES-SCREEN-144',body_bytes=len(body),
      chr_sha256=hashlib.sha256(chr_data).hexdigest(),packet_bytes=2008,program_bytes=len(compact),
      physical_approved=False,scope='Readable NES CHR atlas with unchanged NCR1 live path; no repeated A/B/C comparison, no input/audio.'),indent=2)+'\n')
    return out/'screen-program.hex'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--chr-hex',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();build(bytes(int(x,16) for x in a.chr_hex.read_text().split()),a.out)
