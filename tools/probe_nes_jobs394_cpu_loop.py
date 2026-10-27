# SPDX-License-Identifier: MIT
"""Run twelve output frames without resetting the actual65816 or its WRAM.
The SPI/source availability is a fixture;this is a CPU lifecycle proof only."""
import argparse,json,os,struct,subprocess
from pathlib import Path
import probe_nes_jobs394_native as n
from nes_delta231 import sha

def literal(x):
 if isinstance(x,dict):return '{'+','.join('['+json.dumps(k)+']='+literal(v)for k,v in x.items())+'}'
 if isinstance(x,list):return '{'+','.join(map(literal,x))+'}'
 if isinstance(x,bool):return str(x).lower()
 return json.dumps(x)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--arm',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);body,labels=n.rom(d);oracle,_=n.plans();scenes=[]
 for f in range(905,917):
  expected=(oracle/f'expected-{f-904}.bin').read_bytes();jobs=n.fixtures(f,a.arm)
  jobs=[dict(record=j['record'],data=j['data'],offset=j['offset'],first=j['first'],last=j['last'],token=j['token'])for j in jobs]
  scenes.append(dict(frame=f,JOBS=jobs,VIEW=list(n.current_view(f)),CONTEXT=list(struct.pack('<IHBB',f-904,f-904,(f-905)%2,int(f<907))),BANK=(f-905)%2,COLD=f<907,FINAL_TOKEN=len(jobs)+1,EXPECTMAP=expected[:4096].hex(),EXPECTCG=expected[4096:4608].hex(),EXPECTOAM=expected[4608:5152].hex(),EXPECTHDMA=expected[5152:].hex()))
 keys=('JOBS','VIEW','CONTEXT','BANK','COLD','FINAL_TOKEN','EXPECTMAP','EXPECTCG','EXPECTOAM','EXPECTHDMA')
 header='local OUT='+json.dumps(d.as_posix())+'\nlocal SCENES='+literal(scenes)+'\nlocal cursor=1\nlocal STOP=false\nlocal '+','.join(keys)+'\n'
 header+='local function activate()local s=SCENES[cursor];'+ ';'.join(k+'=s.'+k for k in keys)+' end\nactivate()\n'
 header+='local INITMAP=string.rep("00",4096)\nlocal INITCG=string.rep("00",512)\nlocal INITOAM=string.rep("00",544)\nlocal INITHDMA=string.rep("00",3418)\n'
 header+='local LABELS='+literal(labels)+'\n'
 lua=n.LUA.replace('for _,j in ipairs(JOBS)do j.r=bytes(j.record);j.payload=bytes(j.data)end','for _,s in ipairs(SCENES)do for _,j in ipairs(s.JOBS)do j.r=bytes(j.record);j.payload=bytes(j.data)end end')
 start=lua.index("  local out=assert(io.open(OUT..'/cpu-result.json','w'));out:write(string.format(")
 end=lua.index(' elseif a==0x606f then',start)
 lua=lua[:start]+'''  mark('present');cursor=cursor+1
  if cursor>#SCENES then
   local out=assert(io.open(OUT..'/cpu-result.json','w'));out:write('{"passed":true,"frames":12,"reset_count":1,"WRAM_reinitialized_between_frames":false}');out:close();bus:close();timings:close();emu.stop(0)
  else
   activate();at=1;reads=0;staged=0;jobdone=0;viewreads=0;ack={};ppu_start=nil;ppu_end=nil
  end
'''+lua[end:]
 guarded="local original_assert=assert\nfunction assert(v,msg)if not v then local e=io.open(OUT..'/error.txt','a');e:write(tostring(msg)..'\\n'..debug.traceback()..'\\n');e:close();emu.stop(1)end;return original_assert(v,msg)end\n"
 (d/'capture.lua').write_text(header+guarded+lua,newline='\n');(d/'fixtures.json').write_text(json.dumps(scenes,indent=2)+'\n');env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with(d/'mesen.log').open('wb')as log:r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(d/'capture.lua'),str(d/'spool.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-2000:]
 result=json.loads((d/'cpu-result.json').read_text());assert result['passed'];result.update(body_bytes=body,ROM=sha(d/'spool.sfc'),events=sha(d/'events.csv'),fixtures=sha(d/'fixtures.json'),scope=__doc__);(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
