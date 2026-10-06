"""Original Mapper4 video workload variants021. SPDX-License-Identifier: MIT. Derived from project009 diagnostic."""
from pathlib import Path
import argparse,hashlib,json

def build(out,case="baseline"):
 assert case in ("baseline","fine_x","sprite","split","banks32")
 scroll=1 if case=="fine_x" else 0
 chrsize=32768 if case=="banks32" else 16384
 out.mkdir(parents=True,exist_ok=False);code=bytearray();labels={};fix=[]
 def emit(*v):code.extend(v)
 def label(n):labels[n]=0xe000+len(code)
 def lda(v):emit(0xa9,v)
 def sta(a):emit(0x8d,a&255,a>>8)
 def branch(op,n):emit(op,0);fix.append((len(code)-1,n,True))
 def jump(n):emit(0x4c,0,0);fix.append((len(code)-2,n,False))
 def bank(r,v):lda(r);sta(0x8000);lda(v);sta(0x8001)
 emit(0x78,0xd8,0xa2,0xff,0x9a);lda(0)
 for a in [0x2000,0x2001,0x4010,0x4015,0xe000,*range(9)]:sta(a)
 lda(0x40);sta(0x4017)
 for r,v in enumerate([0,2,4,5,6,7,0,3]):bank(r,v)
 lda(0);sta(0xa000);sta(0xa001)
 emit(0xad,0,0xa0);sta(7)
 for name in ['wait1','wait2']:
  label(name);emit(0x2c,2,0x20);branch(0x10,name)
 lda(0x3f);sta(0x2006);lda(0);sta(0x2006)
 for v in [15,33,48,22]*8:lda(v);sta(0x2007)
 lda(0x20);sta(0x2006);lda(0);sta(0x2006);emit(0xa0,4,0xa2,0)
 label('nt');emit(0x8a);sta(0x2007);emit(0xe8);branch(0xd0,'nt');emit(0x88);branch(0xd0,'nt')
 lda(0);sta(0x2003);lda(255);emit(0xa2,0)
 label('oam');sta(0x2004);emit(0xe8);branch(0xd0,'oam')
 if case=="sprite":
  lda(0);sta(0x2003)
  for value in (79,1,0,40):lda(value);sta(0x2004)
 lda(scroll);sta(0x2005);lda(0);sta(0x2005);lda(0x88);sta(0x2000);lda(0x1e if case=="sprite" else 0x0a);sta(0x2001);emit(0x58)
 label('main');emit(0xa5,8);branch(0xf0,'main');lda(0);sta(8)
 emit(0xe6,1)
 if case=="banks32":emit(0xa5,1,0x29,3,0x0a,0x0a,0x0a,0x85,0)
 else:emit(0xa5,0,0x49,8,0x85,0)
 lda(0);sta(0x8000);emit(0xa5,0);sta(0x8001)
 lda(1);sta(0x8000);emit(0xa5,0,0x18,0x69,2);sta(0x8001)
 lda(6);sta(0x8000);emit(0xa5,1,0x29,1);sta(0x8001)
 emit(0x09,0xa0,0x85,5,0xad,0,0x80,0x85,2,0xc5,5);branch(0xf0,'prg_ok');emit(0xe6,4)
 label('prg_ok');lda(0x5a);sta(6);lda(scroll);sta(0x2005);lda(0);sta(0x2005)
 lda(63);sta(0xc000);lda(0);sta(0xc001);sta(0xe001);jump('main')
 label('irq');emit(0x48,0xe6,3);lda(0);sta(0xe000)
 if case=="split":
  lda(0);sta(0x8000);emit(0xa5,0,0x49,8);sta(0x8001)
  lda(1);sta(0x8000);emit(0xa5,0,0x49,8,0x18,0x69,2);sta(0x8001)
 emit(0x68,0x40)
 label('nmi');emit(0xe6,8,0x40)
 for pos,name,relative in fix:
  target=labels[name]
  if relative:
   d=target-(0xe000+pos+1);assert -128<=d<=127;code[pos]=d&255
  else:code[pos:pos+2]=target.to_bytes(2,'little')
 prg=bytearray([0xea])*65536
 for i in range(8):prg[i*8192]=0xa0+i
 prg[7*8192:7*8192+len(code)]=code
 for off,addr in [(0xfffa,labels['nmi']),(0xfffc,0xe000),(0xfffe,labels['irq'])]:prg[off:off+2]=addr.to_bytes(2,'little')
 tiles=[]
 for i in range(chrsize//16):
  t=bytearray(hashlib.sha256(b'Original MMC3 integrated 009\0'+i.to_bytes(2,'little')).digest()[:16]);t[:2]=i.to_bytes(2,'little');tiles.append(bytes(t))
 chrdata=b''.join(tiles);rom=b'NES\x1a'+bytes([4,chrsize//8192,0x40,0])+bytes(8)+prg+chrdata
 (out/'mmc3.nes').write_bytes(rom)
 for n,d in [('prg',prg),('chr',chrdata)]: (out/(n+'.hex')).write_text(''.join(f'{v:02x}\n' for v in d),encoding='utf-8',newline='\n')
 m=dict(candidate='NES-R2-VIDEO-WORKLOADS-021',case=case,original_diagnostic=True,license='MIT',mapper=4,prg_bytes=len(prg),chr_bytes=len(chrdata),code_bytes=len(code),sha256=hashlib.sha256(rom).hexdigest(),builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),labels=labels,scope='Original Mapper4 reference workload; CPU-programmed variant. New Mesen captures only, no new RTL equivalence or commercial input.')
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8',newline='\n');return m
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--case',choices=['baseline','fine_x','sprite','split','banks32'],required=True);a=p.parse_args();print(json.dumps(build(a.out,a.case),indent=2))
