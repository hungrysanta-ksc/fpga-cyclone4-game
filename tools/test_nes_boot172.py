# SPDX-License-Identifier: MIT
"""Actual65816 boot/copy/first BEGIN and injected bad-copy negatives."""
from pathlib import Path
import argparse,json,subprocess,os
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['client','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 size=json.loads((a.client/'build.json').read_bytes())['body_bytes'];results=[]
 for mode,corrupt in [('normal',-1),('first_byte',0),('last_byte',size-1),('spc_failure',-1)]:
  d=(a.out/mode).resolve();d.mkdir()
  lua=r'''
local stage=0
local stages={}
local ack={}
local done=false
local spc=nil
local packet={1,0,0,0,1,0,0,0,12,0,0,0,0,0,0,0}
local function finish()
 local f=assert(io.open(OUT..'/result.json','w'))
 f:write(string.format('{"passed":true,"stage":%d,"stages":"%s","spc":%d,"ack":%s}',stage,table.concat(stages,','),spc or 0,done and 'true' or 'false'));f:close();emu.stop(0)
end
emu.addMemoryCallback(function(a,v)
 if a==0x7000 then
  stage=v;stages[#stages+1]=v
  if v==0xe1 then assert(CORRUPT>=0 and #stages==2);finish()end
  if v==3 then assert(CORRUPT<0 and stages[1]==1 and stages[2]==2);if MODE=='spc_failure' then assert(spc==0xe1)else assert(spc==0xa9)end end
 end
 if a==0x7001 then spc=v end
 if a>=0x6010 and a<=0x601b then ack[a-0x6010+1]=v end
 if a==0x601c then
  assert(stage==3 and v==0xa5 and #ack==12 and ack[1]==0 and ack[2]==1)
  for i=3,10 do assert(ack[i]==packet[i])end
  assert(ack[11]==0x65 and ack[12]==0x9a);done=true;finish()
 end
end,emu.callbackType.write,0,0xffff)
emu.addMemoryCallback(function(a,v)
 if a==0x6000 then return stage==3 and 1 or 0 end
 if a==0x6001 then return 0 end
 return a==0x6004 and 16 or 0
end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)assert(stage==3);return packet[a-0x400000+1]end,emu.callbackType.read,0x400000,0x40000f)
if CORRUPT>=0 then emu.addMemoryCallback(function(a,v)assert(stage==1);return v~1 end,emu.callbackType.read,0x7e2000+CORRUPT,0x7e2000+CORRUPT)end
if MODE=='spc_failure' then emu.addMemoryCallback(function(a,v)return 0 end,emu.callbackType.read,0x2140,0x2141)end
emu.addEventCallback(function()if emu.getState().frameCount>300 then error('boot watchdog')end end,emu.eventType.endFrame)
'''
  (d/'capture.lua').write_text('local OUT='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\nlocal CORRUPT='+str(corrupt)+'\n'+lua,encoding='utf-8')
  env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  with (d/'mesen.log').open('wb') as f:
   r=subprocess.run([str(a.mesen.resolve()),'--testRunner',str(d/'capture.lua'),str((a.client/'sink165.sfc').resolve()),'--timeout=30','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-2000:]
  q=json.loads((d/'result.json').read_bytes());results.append(dict(mode=mode,**q))
 result=dict(passed=True,cases=results,client_sha256=sha(a.client/'sink-program.hex'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_boot172.py','tools/test_nes_boot172.py']},scope='Actual65816 against mailbox model; no physical bus or FIFO performance claim')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(results))
if __name__=='__main__':main()
