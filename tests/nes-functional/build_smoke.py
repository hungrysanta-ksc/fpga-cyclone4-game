"""Generate an original NROM test: checkerboard, pulse tone, joypad and heartbeat.
SPDX-License-Identifier: MIT. No commercial ROM or BIOS dependency.
"""
from pathlib import Path
import argparse,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
code=bytearray();labels={};fix=[]
def emit(*v):code.extend(v)
def label(n):labels[n]=0x8000+len(code)
def branch(op,n):emit(op,0);fix.append((len(code)-1,n,True))
def jump(n):emit(0x4c,0,0);fix.append((len(code)-2,n,False))
def lda(v):emit(0xa9,v)
def sta(v):emit(0x8d,v&255,v>>8)
emit(0x78,0xd8,0xa2,0xff,0x9a) # SEI CLD LDX #FF TXS
lda(0);sta(0x2000);sta(0x2001);sta(0x4010);sta(0);sta(1)
for n in ('wait1','wait2'):
 label(n);emit(0x2c,2,0x20);branch(0x10,n)
lda(0x3f);sta(0x2006);lda(0);sta(0x2006)
palette=[0x0f,0x21,0x30,0x16]*8
for c in palette:lda(c);sta(0x2007)
lda(0x20);sta(0x2006);lda(0);sta(0x2006)
emit(0xa0,4,0xa2,0) # four pages, X=0
label('nt');sta(0x2007);emit(0xe8);branch(0xd0,'nt');emit(0x88);branch(0xd0,'nt')
lda(0);sta(0x2005);sta(0x2005);lda(0x0a);sta(0x2001)
lda(1);sta(0x4015);lda(0xbf);sta(0x4000);lda(0xfd);sta(0x4002);lda(8);sta(0x4003)
label('main');emit(0xe6,0);lda(1);sta(0x4016);lda(0);sta(0x4016)
emit(0xad,0x16,0x40,0x29,1);sta(1);jump('main')
for pos,n,relative in fix:
 target=labels[n]
 if relative:
  offset=target-(0x8000+pos+1);assert -128<=offset<=127;code[pos]=offset&255
 else:code[pos:pos+2]=target.to_bytes(2,'little')
prg=bytearray([0xea])*32768;prg[:len(code)]=code
for pos in (0x7ffa,0x7ffc,0x7ffe):prg[pos:pos+2]=(0x8000).to_bytes(2,'little')
chrdata=bytearray(8192)
for row in range(8):chrdata[row]=0xaa if row%2==0 else 0x55
rom=b'NES\x1a'+bytes([2,1])+bytes(10)+prg+chrdata
(a.out/'diagnostic.nes').write_bytes(rom)
for name,data in [('prg',prg),('chr',chrdata)]:
 (a.out/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data))
(a.out/'manifest.json').write_text(json.dumps({'license':'MIT','original_diagnostic':True,'mapper':0,'prg_bytes':32768,'chr_bytes':8192,'code_bytes':len(code),'sha256':hashlib.sha256(rom).hexdigest(),'checks':['checkerboard','pulse tone','CPU RAM heartbeat','joypad A reflected to RAM 1']},indent=2))
