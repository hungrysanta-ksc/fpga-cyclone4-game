# SPDX-License-Identifier: MIT
"""SNES mailbox receiver -> WRAM local comparison -> dynamic DMA -> token ACK.

Requires a held, whole-packet admitted mailbox, NOT ordinary cartridge SRAM.
6000 ready,6001 STOP,6004/5 length;400000..4000FF immutable packet bytes.
6010..601B ACK bytes,601C=A5 publishes ACK and releases packet. 6002/3 pads.
SPI endpoint and board bus integration remain separate from this client image.
"""
from pathlib import Path
import argparse,json,struct
from build_nes_trace_replay import Code,Asm
from nes_native_local165 import emit,emit_upload,call,OFFSETS,LIMITS
from nes_spc163 import emit as emit_spc

def build(out):
 out.mkdir(parents=True,exist_ok=False);c=Code(0x7e2000)
 c.emit(0x78,0xe2,0x20,0xc2,0x10);c.store(0x7000,2);spc=emit_spc(c)
 for a,v in [(0x2100,128),(0x4200,1),(0x420c,0),(0x2105,0),(0x2106,0),(0x2107,0x41),(0x210b,0),(0x2101,1),(0x212c,0x11),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2132,0xe0),(0x2133,0),(0x2115,128)]:c.store(a,v)
 for a in range(0x2123,0x212c):c.store(a,0)
 c.emit(0xc2,0x20)
 # Only private client metadata. Do not clear bank7F/display memory here.
 for a in list(range(0x1000,0x1040,2))+list(range(0x1080,0x108c,2))+list(range(0x1220,0x123a,2)):c.absolute(0x9c,a)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def cmp(a):c.absolute(0xcd,a)
 def imm(v):c.emit(0xa9);c.word(v)
 def cond(op,label):c.emit(op^0x20,3);c.jump(label)
 def error():c.jump('bad_packet')
 def checkimm(a,v):lda(a);c.emit(0xc9);c.word(v);cond(0xd0,'bad_packet')
 c.label('poll');call(c,'service');lda(0x1236);cond(0xd0,'quiet')
 c.emit(0xe2,0x20);lda(0x6000);c.emit(0x29,1,0xc2,0x20);cond(0xf0,'poll')
 lda(0x6004);sta(0x122c);c.emit(0xc9,16,0);cond(0x90,'bad_header');c.emit(0xc9,1,1);cond(0xb0,'bad_header')
 c.emit(0xa2,0,0);c.label('header');c.long(0xbf,0x400000);c.absolute(0x9d,0x1200);c.emit(0xe8,0xe8,0xe0,16,0);c.branch(0xd0,'header')
 checkimm(0x120e,0);lda(0x120c);c.emit(0xc9,241,0);cond(0xb0,'bad_packet')
 c.emit(0x18,0x69,16,0);cmp(0x122c);cond(0xd0,'bad_packet')
 lda(0x1200);c.emit(0x29,255,0,0xc9,1,0);cond(0xf0,'begin')
 checkimm(0x1228,1)
 for a,b in [(0x1202,0x1220),(0x1204,0x1222),(0x1206,0x1224),(0x1208,0x1226)]:lda(a);cmp(b);cond(0xd0,'bad_packet')
 lda(0x1200);c.emit(0x29,255,0,0xc9,2,0);cond(0xf0,'data')
 c.emit(0xc9,3,0);cond(0xf0,'seal');error()
 c.label('begin');checkimm(0x1228,0);checkimm(0x1200,1);checkimm(0x1202,0);checkimm(0x120a,0);checkimm(0x120c,0)
 # Exact monotonically increasing32-bit serial, exhausted until common reset.
 lda(0x1222);c.emit(0x18,0x69,1,0);sta(0x1230)
 lda(0x1224);c.emit(0x69,0,0);cond(0xb0,'bad_packet');cmp(0x1206);cond(0xd0,'bad_packet')
 lda(0x1230);cmp(0x1204);cond(0xd0,'bad_packet')
 for a,b in [(0x1204,0x1222),(0x1206,0x1224),(0x1208,0x1226)]:lda(a);sta(b)
 c.absolute(0x9c,0x1220);imm(1);sta(0x1228)
 for a in range(0x1080,0x108c,2):c.absolute(0x9c,a)
 lda(0x1024);c.emit(0x29,255,0);cond(0xf0,'first_base')
 lda(0x1022);c.emit(0x49,0,0x80);c.jump('base_ready')
 c.label('first_base');imm(0)
 c.label('base_ready');sta(0x1020);c.jump('accepted')
 c.label('data');lda(0x1201);c.emit(0x29,255,0,0xc9,6,0);cond(0xb0,'bad_packet');c.emit(0x0a,0xaa)
 c.absolute(0xbd,0x1080);cmp(0x120a);cond(0xd0,'bad_packet')
 lda(0x120c);cond(0xf0,'bad_packet');c.emit(0x18);c.absolute(0x6d,0x120a);cond(0xb0,'bad_packet');sta(0x1234)
 pos=len(c.data);c.long(0xdf,0);limitfix=pos+1;cond(0x90,'data_size_ok');cond(0xd0,'bad_packet')
 c.label('data_size_ok');lda(0x1234);c.absolute(0x9d,0x1080)
 pos=len(c.data);c.long(0xbf,0);offsetfix=pos+1;c.emit(0x18);c.absolute(0x6d,0x1020);c.absolute(0x6d,0x120a);sta(0x2181)
 c.emit(0xe2,0x20);c.store(0x2183,1)
 for a,v in [(0x4300,0),(0x4301,0x80),(0x4302,16),(0x4303,0),(0x4304,0x40)]:c.store(a,v)
 c.emit(0xc2,0x20);lda(0x120c);sta(0x4305);c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20);c.jump('accepted')
 c.label('seal');checkimm(0x1200,3);checkimm(0x120a,0);checkimm(0x120c,18)
 c.emit(0xa2,0,0);c.label('seal_sizes');c.long(0xbf,0x400010);c.absolute(0xdd,0x1080);cond(0xd0,'bad_packet');c.absolute(0x9d,0x1000)
 c.emit(0xe8,0xe8,0xe0,12,0);c.branch(0xd0,'seal_sizes')
 for a,b in [(0x40001c,0x102c),(0x40001e,0x102e),(0x400020,0x1030)]:c.long(0xaf,a);sta(b)
 call(c,'local165_entry');lda(0x1236);cond(0xd0,'stop_packet');call(c,'upload165_entry')
 c.emit(0xe2,0x20);lda(0x1025);c.emit(0xc9,3,0xc2,0x20);cond(0xd0,'compare_failed')
 # Retire only after actual local DMA; no host-injected display acknowledgement.
 for a in range(0,12,2):lda(0x1000+a);sta(0x1010+a)
 lda(0x1020);sta(0x1022);c.emit(0xe2,0x20);c.store(0x1024,1);c.emit(0xc2,0x20)
 c.absolute(0x9c,0x1228);imm(1);c.jump('reply')
 c.label('accepted');imm(0);c.jump('reply')
 c.label('compare_failed');lda(0x1025);c.emit(0x29,255,0);c.jump('fail')
 c.label('stop_packet');imm(0xe4);c.jump('fail')
 c.label('bad_packet');imm(0xe0);c.jump('fail')
 c.label('bad_header');c.jump('quiet') # no trustworthy token to ACK
 c.label('fail');sta(0x122a);imm(2);sta(0x1228);lda(0x122a)
 c.label('reply');c.emit(0xe2,0x20);sta(0x6010);lda(0x1200);sta(0x6011);c.emit(0xc2,0x20)
 for i in range(0,8,2):lda(0x1202+i);sta(0x6012+i)
 imm(0x9a65);sta(0x601a);c.emit(0xe2,0x20);c.store(0x601c,0xa5);c.emit(0xc2,0x20)
 c.absolute(0xee,0x1220);lda(0x1228);c.emit(0xc9,2,0);cond(0xf0,'quiet');c.jump('poll')
 c.label('quiet');call(c,'service');c.jump('quiet')
 local=emit(c,service='service');upload=emit_upload(c)
 # Preserve widths/scratch; no nested receive or reuse during local compare.
 c.label('service');c.emit(0x08,0xe2,0x20);lda(0x6001);c.emit(0x29,0x80);cond(0xf0,'service_pad')
 c.store(0x1236,1)
 c.label('service_pad');lda(0x4212);c.branch(0x30,'service_blank');c.store(0x1238,0);c.branch(0x80,'service_done')
 c.label('service_blank');c.emit(0x89,1);c.branch(0xd0,'service_done');lda(0x1238);c.branch(0xd0,'service_done')
 for a,b in [(0x4218,0x6002),(0x4219,0x6003)]:lda(a);sta(b)
 c.store(0x1238,1)
 c.label('service_done');c.emit(0x28,0x60)
 for values,pos in [(LIMITS,limitfix),(OFFSETS,offsetfix)]:
  c.data[pos:pos+3]=(c.base+len(c.data)).to_bytes(3,'little')
  for v in values:c.word(v)
 body=c.finish();assert len(body)<=0xec0
 rom=bytearray([255])*32768;rom[0x100:0x100+len(body)]=body
 boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab)
 for a,v in [(0x2100,128),(0x4200,0),(0x420c,0)]:boot.store(a,v)
 boot.emit(0xc2,0x20,0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x8100);boot.emit(0xa0);boot.word(0x2000)
 boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000);rom[:len(boot.finish())]=boot.finish()
 rom[0x7fc0:0x7fd5]=b'NES WRAM SINK165'.ljust(21,b' ');rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
 for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
 checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
 (out/'sink165.sfc').write_bytes(rom);compact=rom[:4096];compact[0xfc0:0x1000]=rom[0x7fc0:]
 (out/'sink-program.hex').write_text(''.join(f'{b:02x}\n' for b in compact))
 result=dict(body_bytes=len(body),program_bytes=4096,spc=spc,local=local,upload=upload,mailbox_bytes=256,scope='SNES executable client; requires new bus decode and checked immutable packet transport. Not installable on164 bus ROM mapping.')
 (out/'build.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
