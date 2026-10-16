# SPDX-License-Identifier: MIT
"""Actual194 65816 DMA/SEAL vs archived186 C-generated seven-scene pixels.

Held descriptor/aperture bus is a Lua fixture, not RTL or live game. No memory,
PPU, or ACK injection. Requests/tiles originate from immutable186 C evidence.
"""
from pathlib import Path
import argparse,hashlib,json,os,struct,subprocess
from nes_clip178 import replace
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def word(b,i):return int.from_bytes(b[i:i+2],'little')

def prepare(ref,out):
 source=[p.read_bytes() for p in sorted(ref.glob('req-*.bin'))];result=[];tiles={};sequence=0;token=0x19400000;i=0
 while i<len(source):
  p=bytearray(source[i]);i+=1
  if p[0]==1:sequence=0
  if p[0] in (2,4,5) and p[1]<2:
   def expand(q):return q[16:] if q[0]==2 else q[16:18]*(word(q,14)//2)
   payload=bytearray(expand(p));offset=word(p,10)
   while i<len(source):
    q=source[i]
    if q[0] not in (2,4,5) or q[1]!=p[1] or word(q,8)!=word(p,8) or word(q,10)!=offset+len(payload):break
    payload.extend(expand(q));i+=1
   # Exercise maximum DMA and multi-chunk section without changing any used
   # tile. These appended unused zero tiles do not alter the expected pixels.
   if word(p,8)==12 and p[1]==0:payload.extend(bytes(4096-len(payload)))
   for at in range(0,len(payload),2048):
    raw=bytes(payload[at:at+2048]);q=bytearray(p[:16]);q[0]=7
    struct.pack_into('<HHH',q,10,offset+at,4,len(raw));q.extend(struct.pack('<I',token));token+=1
    struct.pack_into('<H',q,2,sequence);sequence+=1
    result.append(bytes(q));tiles[len(result)]=raw
   continue
  if p[0]==3:
   struct.pack_into('<H',p,36,0x1941)
   if word(p,8)==12:struct.pack_into('<H',p,16,4096)
  struct.pack_into('<H',p,2,sequence);sequence+=1;result.append(bytes(p))
 for n,p in enumerate(result,1):(out/f'req-{n:04}.bin').write_bytes(p)
 for n,b in tiles.items():(out/f'tile-{n:04}.bin').write_bytes(b)
 return dict(requests=len(result),chunks=len(tiles),tile_bytes=sum(map(len,tiles.values())),max_chunk=max(map(len,tiles.values())))

def script(ref):
 s=(ref/'capture.lua').read_text(encoding='utf8').split('\n',2)[2]
 s=replace(s,'local rejected=false',"local rejected=false\nlocal tile=nil;local consumed=false;local reads=0;local retires=0;local tokenWrites={};local maximumDma=0")
 s=replace(s,'packet=nil;ordinal=ordinal+1;pendingAck=nil',"packet=nil;tile=nil;consumed=false;reads=0;tokenWrites={};ordinal=ordinal+1;pendingAck=nil")
 s=replace(s,' if a==0x6001 then'," if a==0x6001 then\n  if MODE=='stop_dma' and packet and pb(0)==7 and pw(8)==13 and reads>0 then return 128 end")
 anchor='emu.addMemoryCallback(function(a,v)return a==0x4218 and 0 or 4 end,emu.callbackType.read,0x4218,0x4219)'
 extra=r'''
local function descriptor()
 if not tile or consumed then return string.rep(string.char(0),12)end
 local b={1,pb(1),pw(14)&255,pw(14)>>8,pb(10),pb(11),pb(8),pb(9),pb(16),pb(17),pb(18),pb(19)}
 if pw(8)==13 then
  if MODE=='bad_ready' then b[1]=0 end
  if MODE=='bad_kind' then b[2]=1-b[2] end
  if MODE=='bad_length' then b[3]=b[3]~16 end
  if MODE=='bad_offset' then b[5]=b[5]~16 end
  if MODE=='bad_generation' then b[7]=b[7]~1 end
  if MODE=='bad_token' then b[9]=b[9]~1 end
 end
 return string.char(table.unpack(b))
end
emu.addMemoryCallback(function(a,v)return descriptor():byte(a-0x6040+1)end,emu.callbackType.read,0x6040,0x604b)
emu.addMemoryCallback(function(a,v)
 assert(tile and not consumed,'unowned bulk read')
 local i=a-0x400800;assert(i<#tile,'bulk overread');assert(i==reads,'nonsequential DMA')
 reads=reads+1;return tile:byte(i+1)
end,emu.callbackType.read,0x400800,0x400fff)
emu.addMemoryCallback(function(a,v)
 assert(tile and not consumed,'unowned consume write')
 if a<0x6050 then tokenWrites[a-0x604c+1]=v else
  assert(v==0xa5 and #tokenWrites==4 and reads==#tile,'early consume')
  for i=1,4 do assert(tokenWrites[i]==pb(15+i),'wrong consume token')end
  consumed=true;retires=retires+1;maximumDma=math.max(maximumDma,reads)
 end
end,emu.callbackType.write,0x604c,0x6050)
'''
 s=replace(s,anchor,anchor+'\n'+extra)
 s=replace(s,'pb(0)==5 or pb(0)==6)', 'pb(0)==5 or pb(0)==6 or pb(0)==7)')
 s=replace(s,'local expected=pb(0)==6 and rd((base~0x8000)+i) or pb(16+(pb(0)>=4 and (i%2) or i))',
             'local expected=pb(0)==7 and tile:byte(i+1) or (pb(0)==6 and rd((base~0x8000)+i) or pb(16+(pb(0)>=4 and (i%2) or i)))')
 s=replace(s,'  acks=acks+1;',"  if pb(0)==7 then\n   if ack[1]==0 then assert(consumed and reads==#tile)else assert(not consumed)end\n  end\n  acks=acks+1;")
 start=s.index(" if packet:byte(1)==6 and pw(8)==13 then")
 end=s.index(' local f=io.open(OUT_DIR',start)
 s=s[:start]+""" if pb(0)==7 then
  local t=assert(io.open(string.format(OUT_DIR..'/tile-%04d.bin',ordinal),'rb'));tile=t:read('*a');t:close()
  if pw(8)==13 then
   local b={packet:byte(1,#packet)}
   if MODE=='bad_expanded' then b[15]=16;b[16]=8 end
   if MODE=='bad_align' then b[15]=15;b[16]=0 end
   if MODE=='bad_section' then b[2]=2 end
   if MODE=='bad_physical' then b[13]=2 end
   packet=string.char(table.unpack(b))
  end
 end
 end end
"""+s[end:]
 s=replace(s," local f=io.open(OUT_DIR..'/producer-done.txt','r')\n if f then\n  f:close();", " if not packet and (rejected or ordinal>TOTAL) then\n  ")
 s=replace(s,"assert(commits==((MODE=='reference' or MODE=='inherit') and 7 or 1))", "assert(commits==(MODE=='normal' and 7 or 1));assert(maximumDma==2048);assert(retires>0)")
 s=replace(s,"local o=assert(io.open(OUT_DIR..'/consumer-result.json','w'));o:write(string.format(","local o=assert(io.open(OUT_DIR..'/consumer-result.json','w'));o:write(string.format(")
 s=replace(s,'"max_repeat_service_bytes":%d}', '"max_repeat_service_bytes":%d,"retired_chunks":%d,"max_dma":%d}')
 s=replace(s,'held,maxServiceBytes));o:close()', 'held,maxServiceBytes,retires,maximumDma));o:close()')
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ('out','client','mesen'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--modes',nargs='+',default=['normal','bad_ready','bad_kind','bad_length','bad_offset','bad_generation','bad_token','stop_dma'])
 a=p.parse_args();a.out=a.out.resolve();a.client=a.client.resolve();a.mesen=a.mesen.resolve();a.out.mkdir(parents=True,exist_ok=False)
 ref=ROOT.parent/'probes/nes-copy186/evidence/coupled03/inherit';lua=script(ref)
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet';cases=[]
 for mode in a.modes:
  d=a.out/mode;d.mkdir();prepared=prepare(ref,d)
  (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\nlocal TOTAL='+str(prepared['requests'])+'\n'+lua,encoding='utf8',newline='\n')
  with (d/'mesen.log').open('wb') as f:
   r=subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.client/'sink165.sfc'),'--timeout=50','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-4000:]
  result=json.loads((d/'consumer-result.json').read_bytes());result.update(mode=mode,prepared=prepared)
  for i in range(1,8 if mode=='normal' else 2):assert (d/f'frame-{i}.rgb').read_bytes()==(ref/f'frame-{i}.rgb').read_bytes(),(mode,i)
  cases.append(result);print(json.dumps(result),flush=True)
 result=dict(passed=True,cases=cases,client_sha256=sha(a.client/'sink165.sfc'),mesen_sha256=sha(a.mesen),generator_sha256=sha(Path(__file__)),
  reference_pins={f.name:sha(f) for f in ref.iterdir() if f.suffix in ('.bin','.rgb','.lua')},scope=__doc__,actual_scroll=False,physical=False,rtl_bus_coupled=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
