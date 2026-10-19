# SPDX-License-Identifier: MIT
"""Actual65816 cache/carry/identity guards with an explicit mock bus.

No RTL or physical timing claims. The separate coupled run verifies the same
ROM against the real queue, aperture, receipts and display lease.
"""
import argparse,json,os,subprocess,shutil
from pathlib import Path
from probe_nes_common263 import rom
from nes_delta231 import ROOT,sha

LUA=r'''
local chunk=0;local writes={};local reads=0;local tokenReads=0;local start=nil
local function tok()return SEED+chunk end
local function remaining()return chunk<47 and 47-chunk or 64-chunk end
emu.addMemoryCallback(function(a,v)
 local off=a-0x400800;return (chunk*64+off)%256
end,emu.callbackType.read,0x400800,0x400fff)
emu.addMemoryCallback(function(a,v)
 if a==0x6040 then if chunk<64 then if not start then start=emu.getState().masterClock end;return 1 else return 0 end end
 if a==0x6052 then return chunk==64 and 1 or 0 end
 if a==0x6053 then return BAD==3 and 0 or BAD==4 and 48 or remaining() end
 if a==0x6041 then reads=reads+1;return BAD==1 and 6 or 2 end
 if a==0x6042 then return 64 end;if a==0x6043 then return 0 end
 if a==0x6044 then return (chunk*32)%256 end;if a==0x6045 then return math.floor(chunk*32/256) end
 if a==0x6046 then reads=reads+1;return BAD==2 and 2 or 1 end;if a==0x6047 then reads=reads+1;return 0 end
 if a>=0x6048 and a<=0x604b then tokenReads=tokenReads+1;local t=chunk==64 and SEED+63 or tok();return math.floor(t/2^(8*(a-0x6048)))%256 end
 return 0
end,emu.callbackType.read,0x6040,0x6053)
emu.addMemoryCallback(function(a,v)
 if a>=0x604c and a<=0x604f then writes[a-0x604c]=v end
 if a==0x6050 or a==0x6058 then
  local t=0;for i=0,3 do assert(writes[i]~=nil);t=t+writes[i]*2^(8*i) end
  assert(t==(a==0x6050 and tok() or SEED+63),'cached32bit token mismatch');writes={}
 end
 if a==0x6050 then assert(v==0xa5 and chunk<64);chunk=chunk+1 end
 if a==0x6057 or a==0x6058 then
  assert((BAD>0 and a==0x6057 and chunk==0) or (BAD==0 and a==0x6058 and chunk==64))
  if BAD==0 then for i=0,4095 do assert(emu.read(0x8000+i,emu.memType.snesVideoRam)==i%256) end end
  local f=assert(io.open(OUT..'/result.json','w'));f:write(string.format('{"passed":true,"bad":%d,"chunks":%d,"identity_reads":%d,"token_reads":%d,"final_clock":%d}',BAD,chunk,reads,tokenReads,emu.getState().masterClock));f:close();emu.stop(0)
 end
end,emu.callbackType.write,0x604c,0x6058)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet';cases=[]
 for i,(cached,seed,bad) in enumerate([(False,65520,0),(True,65520,0),(True,16777200,0),(True,0xffffffb0,0),*[(True,1,b) for b in range(1,5)]]):
  sub=d/f'case{i:02}';sub.mkdir();size=rom(sub,cached)
  script='local OUT='+json.dumps(sub.as_posix())+f'\nlocal SEED={seed};local BAD={bad}\n'+LUA
  (sub/'run.lua').write_text(script,encoding='utf-8',newline='\n')
  with (sub/'mesen.log').open('wb') as log:r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(sub/'run.lua'),str(sub/'joint.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],stdout=log,stderr=subprocess.STDOUT,cwd=sub,env=env,creationflags=subprocess.CREATE_NO_WINDOW,timeout=45)
  assert r.returncode==0,(sub/'mesen.log').read_text(errors='replace')[-2000:]
  result=json.loads((sub/'result.json').read_text());assert result['passed'];result.update(cached=cached,seed=seed,rom_bytes=size,rom_sha256=sha(sub/'joint.sfc'));cases.append(result)
 assert cases[0]['identity_reads']==192 and cases[1]['identity_reads']==6
 assert cases[0]['token_reads']==260 and cases[1]['token_reads']==12
 result=dict(passed=True,cases=cases,scope=__doc__,source_sha256=sha(ROOT/'tools/probe_nes_common263.py'),physical=False)
 shutil.copyfile(__file__,d/'guard_nes_common263.py');(d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
