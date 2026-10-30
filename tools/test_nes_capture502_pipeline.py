# SPDX-License-Identifier: MIT
"""502 fixed PPU fixture -> actual source records -> deployed493 M4/65816.

SPI packetization, ACK endpoint and CHR response are fixtures. Instruction
counts and file-aperture CPU clocks are separate; no full RUN/IRQ/ROM/FPS proof.
"""
import argparse,json,os,re,shutil,struct,subprocess
from collections import Counter
from pathlib import Path
from audit_nes_output489 import CompactAudit
from check_nes_game478 import sha
from unicorn.arm_const import UC_ARM_REG_R1,UC_ARM_REG_R3
from test_nes_output489_snes import LUA,packet
ROOT=Path(__file__).resolve().parents[1]

class Linked(CompactAudit):
 def __init__(self,*args):
  self.source_wire=Counter();super().__init__(*args)
 def hook(self,u,at,size,user):
  if at==self.spi:
   op=u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]
   self.source_wire[f'{op:02x}']+=u.reg_read(UC_ARM_REG_R3)
  super().hook(u,at,size,user)

def source(d):
 m=json.loads((d/'inputs.json').read_text());r=json.loads((d/'result.json').read_text())
 assert r['completed'] and sha(d/'inputs.json')==r['inputs_SHA256']
 assert len(m['cases'])==1
 for n,h in m['sources'].items():assert sha(d/n)==h,n
 stem=m['cases'][0]['name']+'.txt'
 q=d/(stem+'.queries502.txt');wire=d/(stem+'.records502.txt')
 lines=q.read_text().splitlines();counts=list(map(int,lines[0].split()[1:]));assert len(counts)==7
 widths=[2,1,8,4,8,1];caps=[1056,224,128,128,224,64]
 offsets=[];at=0
 for w,c in zip(widths,caps):offsets.append(at);at+=w*c
 assert at==5728
 geometry=bytearray(5741);raw=bytearray(counts[6]*256);seen=set()
 for line in lines[1:]:
  k,i,v=line.split();k=int(k);i=int(i);v=int(v,16);assert (k,i)not in seen;seen.add((k,i))
  if k==7:raw[i]=v
  else:
   assert i<counts[k]<=caps[k];p=offsets[k]+i*widths[k];geometry[p:p+widths[k]]=v.to_bytes(widths[k],'little')
 assert len(seen)==sum(counts[:6])+len(raw)
 struct.pack_into('<6HB',geometry,5728,*counts)
 records=[];generations=set();logical=[]
 for line in wire.read_text().splitlines():
  v=int(line,16);kind=v>>93;gen=(v>>77)&65535;index=(v>>64)&8191;data=v&((1<<64)-1)
  width=8 if kind==0 and index&4096 else [2,1,7,4,7,1,2,8][kind]
  records.append(struct.pack('>HH',(kind<<13)|index,gen)+data.to_bytes(width,'big'));generations.add(gen);logical.append((kind,index))
 assert generations=={1} and logical[-1]==(7,3)
 packets=[];b=bytearray()
 for record in records[:-1]:
  if len(b)+len(record)>256:packets.append(bytes(b));b.clear()
  b+=record
 if b:packets.append(bytes(b))
 packets.append(records[-1])
 return bytes(geometry),bytes(raw),packets,dict(query_SHA256=sha(q),records_SHA256=sha(wire),inputs_SHA256=sha(d/'inputs.json'),counts=counts,records=len(records),packet_count=len(packets),payload_B=sum(map(len,packets)))

def arm(a):
 a.out.mkdir(parents=True,exist_ok=False)
 known=json.loads((ROOT/'analysis/boot493-verification.json').read_text())
 assert sha(a.arm/'obj-nes-100/firmware.stm')==known['ARM']['firmware_SHA256']
 palette=struct.pack('<64H',*map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(),re.S)[1].split(',')))
 rows=[]
 for name,src in [('501',a.export501),('502',a.export502)]:
  d=a.out/name;d.mkdir();geometry,raw,packets,pins=source(src)
  (d/'geometry.bin').write_bytes(geometry);(d/'raw.bin').write_bytes(raw)
  m=Linked(a.arm,palette,d);result=m.frame(packets,geometry,raw,1,1)
  (d/'frame1/plans.json').write_text(json.dumps(result['plans'])+'\n',newline='\n')
  result.pop('plans');row=dict(variant=name,source=pins,ARM=result,serializer=m.rows[-1],source_SPI_wire_B=dict(m.source_wire))
  (d/'result.json').write_text(json.dumps(row,indent=2)+'\n',newline='\n');rows.append(row)
  print(json.dumps(row),flush=True)
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,scope=__doc__,firmware_SHA256=known['ARM']['firmware_SHA256'],rows=rows),indent=2)+'\n',newline='\n')

def cpu(a):
 assert sha(a.client)==json.loads((ROOT/'analysis/output489-verification.json').read_text())['SNES']['client_SHA256']
 a.out.mkdir(parents=True,exist_ok=False);summary=[]
 for name in ['501','502']:
  src=a.input/name/'frame1';d=a.out/name;d.mkdir();batch=[]
  batch.append((packet(1,0,1,1,0,struct.pack('<HHII',0x4891,0,0,1)),None))
  def chrbyte(at):
   at&=8191;return (at&255)^((at>>6)&255)^0xb3
  for token,(_,h)in enumerate(json.loads((src/'plans.json').read_text())):
   q=bytes.fromhex(h);gen,slot,tag,kind,mask=struct.unpack_from('<HHHBB',q);assert gen==1
   size=32 if kind==1 else 16;tile=bytearray(size)
   if kind!=2:
    alt=struct.unpack_from('<8H',q,24)
    for y in range(8):
     if mask&(1<<y):
      tile[2*y]=chrbyte((tag if alt[y]==65535 else alt[y])*16+q[8+2*y]);tile[2*y+1]=chrbyte(tag*16+8+q[9+2*y])
   batch.append((packet(7,int(kind==1),1,1,slot*size,struct.pack('<I',token),size),bytes(tile)))
  # Retain496's existing contiguous<=2048B append rule. Do not charge one
  # artificial bulk command per tile plan. Producer readiness remains modeled.
  original=[(b[1],int.from_bytes(b[10:12],'little'),t)for b,t in batch if t is not None]
  merged=[]
  for b,t in batch:
   b=bytearray(b)
   if t is not None and merged and merged[-1][1] is not None:
    old,data=merged[-1]
    if old[1]==b[1] and old[8:10]==b[8:10] and int.from_bytes(old[10:12],'little')+len(data)==int.from_bytes(b[10:12],'little') and len(data)+len(t)<=2048:
     merged[-1]=(old,data+t);struct.pack_into('<H',old,14,len(data)+len(t));continue
   merged.append((b,t))
  rebuilt=[];token=0
  for b,t in merged:
   if t is None:continue
   struct.pack_into('<I',b,16,token);token+=1;size=32 if b[1]else 16;offset=int.from_bytes(b[10:12],'little')
   rebuilt.extend((b[1],offset+i,t[i:i+size])for i in range(0,len(t),size))
  assert rebuilt==original
  (d/'bulk.json').write_text(json.dumps(dict(plans=len(original),chunks=token,ordered_tiles_equal=True,rule='496 existing contiguous same section/generation <=2048B; readiness modeled'))+'\n',newline='\n')
  batch=merged
  batch.extend((p.read_bytes(),None)for p in sorted(src.glob('packet*.bin')))
  requests=[]
  for seq,(b,tile)in enumerate(batch):
   b=bytearray(b);struct.pack_into('<H',b,2,seq);requests.append(bytes(b))
   (d/f'req-{seq+1:04d}.bin').write_bytes(b)
   if tile is not None:(d/f'tile-{seq+1:04d}.bin').write_bytes(tile)
  (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b in requests))
  shutil.copy2(src/'expected-hdma.bin',d/'expected-1.bin');shutil.copy2(a.client,d/'client.sfc')
  lua=LUA.replace('-905','-1')
  for key,value in dict(ROOT=json.dumps(d.as_posix()),MODE='"normal"',COMPACT='true',TOTAL=len(batch),FRAMES=1,SCHEDULE='"fixed"',START=a.start_clock,FAULT=2,POISON='false').items():lua=lua.replace('@'+key+'@',str(value))
  error=json.dumps((d/'error.txt').as_posix())
  diag="local function fatal(m)local f=io.open("+error+",'a');if f then f:write(tostring(m)..'\\n'..debug.traceback()..'\\n');f:close()end;emu.stop(1)end\nlocal mem,event=emu.addMemoryCallback,emu.addEventCallback\nemu.addMemoryCallback=function(fn,...)return mem(function(a,v)local ok,r=pcall(fn,a,v);if not ok then fatal(r);return 0 end;return r end,...)end\nemu.addEventCallback=function(fn,...)return event(function(...)local ok,r=pcall(fn,...);if not ok then fatal(r)end;return r end,...)end\n"
  (d/'capture.lua').write_text(diag+lua,encoding='utf8',newline='\n')
  env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  with (d/'mesen.log').open('wb')as log:
   r=subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(d/'client.sfc'),'--timeout=240','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=250,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(name,r.returncode,(d/'error.txt').read_text()if(d/'error.txt').exists()else(d/'mesen.log').read_text())
  result=json.loads((d/'result.json').read_text());assert result['passed'] and result['commits']==1
  result.update(variant=name,requests=len(requests),E1_wire_B=sum(len(b)+3 for b in requests),client_SHA256=sha(d/'client.sfc'),pixels_SHA256=sha(d/'frame-1.rgb'));summary.append(result)
  print(json.dumps(result),flush=True)
 equal=(a.out/'501/frame-1.rgb').read_bytes()==(a.out/'502/frame-1.rgb').read_bytes()
 (a.out/'result.json').write_text(json.dumps(dict(passed=equal,scope=__doc__,start_masterclock=a.start_clock,pixels_equal=equal,rows=summary,common_ARM_IRQ_ROM_clock=False,physical=False),indent=2)+'\n',newline='\n')
 assert equal,'501/502 final pixels differ; inspect raw images'

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['arm','cpu'])
 for n in ['export501','export502','arm','input','out','client']:p.add_argument('--'+n,type=Path)
 p.add_argument('--mesen',type=Path,default=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe'))
 p.add_argument('--start-clock',type=int,default=3000000)
 a=p.parse_args();a.out=a.out.resolve();(arm if a.mode=='arm'else cpu)(a)
