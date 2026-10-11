# SPDX-License-Identifier: MIT
"""Compact SNES native 8bpp client for final NES PPU pixels (no game assets)."""
from pathlib import Path
import argparse,json,struct
from build_nes_trace_replay import Asm,Code
from nes_spc163 import emit as emit_spc

# Default digital reference palette used by Mesen. Analog NTSC/CRT differs.
# https://github.com/SourMesen/Mesen/blob/master/Libretro/libretro.cpp
RGB='''666666 002A88 1412A7 3B00A4 5C007E 6E0040 6C0600 561D00
333500 0B4800 005200 004F08 00404D 000000 000000 000000
ADADAD 155FD9 4240FF 7527FE A01ACC B71E7B B53120 994E00
6B6D00 388700 0C9300 008F32 007C8D 000000 000000 000000
FFFEFF 64B0FF 9290FF C676FF F36AFF FE6ECC FE8170 EA9E22
BCBE00 88D800 5CE430 45E082 48CDDE 4F4F4F 000000 000000
FFFEFF C0DFFF D3D2FF E8C8FF FBC2FF FEC4EA FECCC5 F7D8A5
E4E594 CFEF96 BDF4AB B3F3CC B5EBF2 B8B8B8 000000 000000'''.split()

def palette():
    colors=[bytes.fromhex(v) for v in RGB]
    return b''.join(struct.pack('<H',(r>>3)|((g>>3)<<5)|((b>>3)<<10)) for r,g,b in colors)

def build(out):
    assert not out.exists();out.mkdir(parents=True)
    c=Code(0x7e2000);c.emit(0x78,0xe2,0x20,0xc2,0x10);c.store(0x7000,2)
    spc=emit_spc(c)
    for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2105,3),(0x2106,0),
                (0x2107,0x70),(0x210b,0),(0x212c,1),(0x212d,0),(0x212e,0),
                (0x212f,0),(0x2130,0),(0x2131,0),(0x2132,0xe0),(0x2133,0)]:c.store(a,v)
    for a in range(0x2123,0x212c):c.store(a,0)
    for a,v in [(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,3)]:c.store(a,v)
    # Static tilemap 0..895, remaining rows unused in 224-line mode.
    c.store(0x2115,0x80);c.store(0x2116,0);c.store(0x2117,0x70)
    c.emit(0xc2,0x20,0xa9,0,0);c.label('map')
    c.absolute(0x8d,0x2118);c.emit(0x1a,0xc9,0x80,3);c.branch(0xd0,'map');c.emit(0xe2,0x20)
    def dma(bank,src,count,port,mode):
        for a,v in [(0x4300,mode),(0x4301,port),(0x4302,src&255),(0x4303,src>>8),
                    (0x4304,bank),(0x4305,count&255),(0x4306,count>>8),(0x420b,1)]:c.store(a,v)
    c.store(0x2121,0);dma(0,0x8700,128,0x22,2)
    c.store(0x4200,1);c.store(0x7000,3)
    c.label('next');c.absolute(0xad,0x6000);c.emit(0x89,1);c.branch(0xf0,'next')
    # Allow auto-joy to finish; a held snapshot crosses to NES with an ACK.
    def pad(label):
        c.label(label);c.absolute(0xad,0x4212);c.emit(0x89,1);c.branch(0xd0,label)
        c.absolute(0xad,0x4218);c.absolute(0x8d,0x6002)
        c.absolute(0xad,0x4219);c.absolute(0x8d,0x6003)
    pad('joy')
    def blank(label):
        c.label(label+'a');c.absolute(0xad,0x4212);c.branch(0x30,label+'a')
        c.label(label+'b');c.absolute(0xad,0x4212);c.branch(0x10,label+'b')
    blank('upload');c.store(0x2100,128);c.store(0x7000,5)
    c.store(0x2115,128);c.store(0x2116,0);c.store(0x2117,0)
    dma(0x40,0x8000,57344,0x18,1)
    # Full-frame DMA exceeds vblank. Reveal only at a following boundary.
    blank('reveal');c.store(0x2100,15);c.store(0x7000,6)
    # Keep an actual game frame visible for6 vblanks before releasing it.
    # This isolates content from full-frame DMA flicker; game logic keeps running.
    c.emit(0xa2,6,0);c.label('hold');blank('holdedge');pad('holdjoy');c.emit(0xca);c.branch(0xd0,'hold')
    c.store(0x6000,0xa5);c.jump('next')
    body=c.finish();assert len(body)<=0x600
    rom=bytearray([255])*32768;rom[0x100:0x100+len(body)]=body;rom[0x700:0x780]=palette()
    boot=Asm(0x8000)
    boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab)
    for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x7000,1)]:boot.emit(0xa9,v,0x8d,a&255,a>>8)
    boot.emit(0xc2,0x20,0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x8100)
    boot.emit(0xa0);boot.word(0x2000);boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
    rom[:len(boot.finish())]=boot.finish();rom[0x7fc0:0x7fd5]=b'NES GAME PIXEL163'.ljust(21,b' ')
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    compact=rom[:2048];compact[0x7c0:0x800]=rom[0x7fc0:0x8000]
    (out/'game163.sfc').write_bytes(rom)
    (out/'game-program.hex').write_text(''.join(f'{b:02x}\n' for b in compact))
    (out/'result.json').write_text(json.dumps(dict(body_bytes=len(body),program_bytes=2048,
      pixels=[256,224],crop=[8,8],dma_bytes=57344,emphasis=False,audio=True,spc=spc,
      scope='Six-vblank visible hold; unchanged full-frame forced-blank DMA. Reduced snapshot age, not60fps or flicker-free presentation.'),indent=2)+'\n')
    return out/'game-program.hex'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
