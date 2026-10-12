# SPDX-License-Identifier: MIT
"""Synthetic fetch descriptors -> real SNES CPU/DMA/PPU, not a live port."""
from pathlib import Path
import argparse,hashlib,json,os,struct,subprocess
from nes_native_commands165 import Consumer,Fetch,Unsupported,reference_rgb
from build_nes_trace_replay import Code
ROOT=Path(__file__).resolve().parents[1]

def fixture(phase):
 tiles={}
 for t in range(40):
  pixels=[[(x*3+y*2+t+(x*y)%3)%4 for x in range(8)] for y in range(8)]
  tiles[t]=bytes(sum(((pixels[y][x]>>p)&1)<<(7-x) for x in range(8)) for p in range(2) for y in range(8))
 pal=tuple(0x0f if c%4==0 else (c*3+9)%0x3d for c in range(32))
 pal2=tuple(0x0f if c%4==0 else (c*5+17)%0x3d for c in range(32))
 rows=[((5 if y<120 else 2)+phase,0x1e,pal if y<120 else pal2) for y in range(224)]
 words=[]
 for y in range(224):
  fy=(y+3+phase)&7;gy=(y+3+phase)//8
  for x in range(33):
   tag=(gy%3)*4+x%4
   if phase and gy==5 and x==7:tag=13
   words.append(Fetch(tag,fy,x,y,x,(x//5+gy)%4,False,0).pack())
 # Different flips, priority, overlapping objects, clipped edges, and a
 # split 8x16 sprite. Coverage holes model actual per-row sprite evaluation.
 objects=[(0,4,20,0,255),(20,18,21,0x41,255),(23,20,22,0x22,255),
  (220,30,23,0xa3,255),(48,70,24,0x82,255),(48,78,25,0x82,255),
  (92,100,26,1,0x96),(252,130,27,0x40,255),(160,-3,28,0x80,255),
  (180,220,29,2,255),(120,117,30,0,255)]
 for y in range(224):
  rank=0
  for x,top,tag,attr,mask in objects:
   fy=(7-(y-top)) if attr&128 else y-top
   if 0<=fy<8 and (mask>>fy)&1:
    words.append(Fetch(tag,fy,256+tag,y,x+(phase if x==20 else 0),attr,True,rank).pack());rank+=1
 return words,rows,tiles

def checks():
 words,rows,tiles=fixture(0);c=Consumer();p=c.prepare(words,rows,tiles)
 assert c.serial==0 and c.initial;c.commit(p)
 w2,r2,t2=fixture(1);q=c.prepare(w2,r2,t2);assert not q['initial']
 before=(c.serial,c.vram,c.oam,c.scroll);rejected=[]
 def reject(name,fn):
  try:fn()
  except Unsupported:rejected.append(name)
  else:raise AssertionError('accepted '+name)
  assert before==(c.serial,c.vram,c.oam,c.scroll)
 reject('budget',lambda:c.prepare(w2,r2,t2,budget=1))
 reject('missing-row-cell',lambda:c.prepare(words[1:],rows,tiles))
 reject('duplicate-cell',lambda:c.prepare(words+[words[0]],rows,tiles))
 reject('missing-pattern',lambda:c.prepare(words,rows,{k:v for k,v in tiles.items() if k!=0}))
 reject('reserved-bits',lambda:c.prepare([1<<63]+words[1:],rows,tiles))
 bad=list(rows);bad[20]=(0,0x1e,tuple([3]*32))
 reject('third-palette',lambda:c.prepare(words,bad,tiles))
 bad=list(rows);bad[0]=(0,0x18,rows[0][2])
 reject('mask-not-supported',lambda:c.prepare(words,bad,tiles))
 bad=[Fetch.unpack(w) for w in words]
 bad=[Fetch(f.tile,0,f.slot,f.row,f.x,f.attr,f.obj,f.rank).pack() if not f.obj else f.pack() for f in bad]
 reject('row-group-overflow',lambda:c.prepare(bad,rows,tiles))
 reject('stale-commit',lambda:c.commit(p))
 c.commit(q);same=c.prepare(w2,r2,t2);assert same['writes']==[]
 before=(c.serial,c.vram,c.oam,c.scroll)
 # Per-row ordering may not be representable by a single SNES OAM list.
 bg=[w for w in words if not Fetch.unpack(w).obj];cyclic=[]
 for y in range(2):
  for i in range(2):cyclic.append(Fetch(20+i,y,0,y,16+i,0,True,i^y).pack())
 reject('sprite-order-cycle',lambda:Consumer().prepare(bg+cyclic,rows,tiles))
 duplicate=[Fetch(20,0,0,0,10+i,0,True,0).pack() for i in range(2)]
 reject('duplicate-sprite-rank',lambda:Consumer().prepare(bg+duplicate,rows,tiles))
 many=[Fetch(20,0,0,y,10,0,True,0).pack() for y in range(129)]
 reject('OAM-overflow',lambda:Consumer().prepare(bg+many,rows,tiles))
 # Seven rows x eight independently masked objects fit the NES eight-per-row
 # rule but would occupy 56 SNES objects on row7 even when transparent there.
 many=[Fetch(20,0,0,y,10+i,0,True,i).pack() for y in range(7) for i in range(8)]
 reject('SNES-evaluation-overflow',lambda:Consumer().prepare(bg+many,rows,tiles))
 return [p,q],dict(rejected=rejected,no_op_writes=0,source_events=len(words))

def build(plans,out):
 c=Code(0x8000);data=bytearray()
 c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab)
 for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2105,0),(0x2106,0),
  (0x2107,0x41),(0x210b,0),(0x2101,1),(0x212c,0x11),(0x212d,0),(0x212e,0),
  (0x212f,0),(0x2130,0),(0x2131,0),(0x2132,0xe0),(0x2133,0),(0x2115,128)]:c.store(a,v)
 for a in range(0x2123,0x212c):c.store(a,0)
 def blank(label):
  c.label(label+'a');c.absolute(0xad,0x4212);c.branch(0x30,label+'a')
  c.label(label+'b');c.absolute(0xad,0x4212);c.branch(0x10,label+'b')
 def upload(w):
  src=0xc000+len(data);data.extend(w.data)
  if w.kind=='vram':
   dest=w.address//2;c.store(0x2116,dest&255);c.store(0x2117,dest>>8);port,mode=0x18,1
  elif w.kind=='cgram':c.store(0x2121,0);port,mode=0x22,2
  elif w.kind=='oam':c.store(0x2102,0);c.store(0x2103,0);port,mode=4,0
  elif w.kind=='hdma':
   c.store(0x2181,w.address&255);c.store(0x2182,w.address>>8);c.store(0x2183,0);port,mode=0x80,0
  else:raise AssertionError(w.kind)
  for a,v in [(0x4300,mode),(0x4301,port),(0x4302,src&255),(0x4303,src>>8),
   (0x4304,0),(0x4305,len(w.data)&255),(0x4306,len(w.data)>>8),(0x420b,1)]:c.store(a,v)
 for i,p in enumerate(plans):
  if i:
   c.label('wait');c.absolute(0xad,0x6000);c.branch(0xf0,'wait');blank('update');c.store(0x420c,0)
  for w in p['writes']:upload(w)
  if i==0:blank('reveal')
  for port,val in zip([0x210d,0x210e],p['scroll_rows'][0]):
   c.store(port,val&255);c.store(port,val>>8)
  for a,v in [(0x4310,3),(0x4311,0x0d),(0x4312,0),(0x4313,0x90),(0x4314,0x7e),(0x420c,2)]:c.store(a,v)
  if i==0:c.store(0x2100,15)
  c.store(0x7000,i+1)
 c.label('done');c.branch(0x80,'done');code=c.finish()
 assert len(code)<0x4000 and len(data)<0x3fc0
 rom=bytearray([255])*32768;rom[:len(code)]=code;rom[0x4000:0x4000+len(data)]=data
 rom[0x7fc0:0x7fd5]=b'NES NATIVE CMD165'.ljust(21,b' ')
 rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
 for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
 checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
 (out/'native.sfc').write_bytes(rom)
 return dict(test_rom_code_bytes=len(code),test_rom_payload_bytes=len(data))

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--mesen',type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 plans,result=checks();result.update(build(plans,a.out))
 lua='local OUT_DIR='+json.dumps(a.out.as_posix())+'\n'+(ROOT/'snes/video_probe/capture_native_commands165.lua').read_text()
 (a.out/'capture.lua').write_text(lua,encoding='utf8')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'mesen.log').open('wb') as f:
  r=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'native.sfc'),'--timeout=40',
   '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],
   env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(a.out/'mesen.log').read_text(errors='replace')[-3000:]
 result['frames']=[]
 for i,p in enumerate(plans):
  expected=bytes(7*256*3)+reference_rgb(*fixture(i))+bytes(8*256*3)
  actual=(a.out/f'frame-{i+1}.rgb').read_bytes();(a.out/f'expected-{i+1}.rgb').write_bytes(expected)
  assert actual==expected,(i,len(actual),sum(a!=b for a,b in zip(actual,expected)))
  result['frames'].append(dict(payload=p['payload'],charged=p['charged'],writes=len(p['writes']),groups=p['groups'],
   fragments=p['fragments'],rgb_sha256=hashlib.sha256(actual).hexdigest()))
 trace=[list(map(int,line.split())) for line in (a.out/'trace.tsv').read_text().splitlines()]
 commits=[line for line in trace if line[0]==0x7000]
 assert len(commits)==2 and commits[1][3]>=225
 result['update_commit_scanline']=commits[1][3]
 result.update(passed=True,active_pixels=2*256*224,scope='Synthetic descriptors and complete PC-supplied CHR; actual SNES CPU/DMA/PPU model. No live FPGA consumer, CHR fill, CDC, game FPS or physical timing proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
