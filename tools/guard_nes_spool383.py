# SPDX-License-Identifier: MIT
"""Actual383CPU STOP at storage/flush/DMA and bounded WRAM admission guards."""
import argparse,json,os,struct,subprocess
from pathlib import Path
import probe_nes_spool383 as native
from nes_delta231 import ROOT,BASE,sha,once


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.out.resolve();root.mkdir(parents=True,exist_ok=False);oracle,_=native.plans();prior=(oracle/'expected-1.bin').read_bytes();expected=(oracle/'expected-3.bin').read_bytes();rows=[]
 for name in ('afterstore','beforeflush','duringPPU','tileoverflow','joboverflow','cgram','densepalettebudget'):
  d=root/name;d.mkdir();body,labels=native.rom(d);jobs=native.fixtures(907);lua=native.LUA;stop=True
  if name=='afterstore':condition='staged>=1';expect='staged==1 and not ppu_start and jobdone==0'
  elif name=='beforeflush':condition='staged>=#JOBS';expect='staged==#JOBS and not ppu_start and jobdone==0'
  elif name=='duringPPU':condition='jobdone>=2';expect='staged==#JOBS and ppu_start and jobdone==2'
  elif name=='tileoverflow':
   condition='false';expect='staged==0 and not ppu_start and jobdone==0';jobs=jobs[:1];j=jobs[0];desc=bytearray.fromhex(j['descriptor']);desc[1:3]=struct.pack('<H',8193);j['descriptor']=desc.hex();j['data']='00'*8193
  elif name=='joboverflow':
   condition='false';expect='staged==256 and not ppu_start and jobdone==0';j=jobs[0];desc=bytearray.fromhex(j['descriptor']);jobs=[]
   for i in range(257):
    desc[7:11]=struct.pack('<I',i+1);jobs.append(dict(j,descriptor=desc.hex(),token=i+1))
  else:
   colors=b''.join(struct.pack('<H',(i*129)&0x7fff) for i in range(256))
   cg=dict(typed=False,descriptor=(bytes([0,3])+struct.pack('<HHH',0x6000,512,0)+b'\x00').hex(),data=colors.hex(),token=999,kind=1,target=0,bank=0)
   if name=='cgram':jobs=[cg];stop=False;condition='false';expect='false'
   else:jobs.append(cg);condition='false';expect='staged==#JOBS and not ppu_start and jobdone==0'
  lua=once(lua,'STOP and staged>=1','STOP and ('+condition+')')
  lua=once(lua,"assert(STOP and v==0xee and not ppu_start and staged==1);", "assert(STOP and v==0xee and ("+expect+"));")
  lua=once(lua,"'{\"passed\":true,\"STOP\":true,\"final_ACK\":false,\"PPU_jobs\":0}'", "string.format('{\"passed\":true,\"STOP_or_capacity_abort\":true,\"final_ACK\":false,\"PPU_jobs\":%d,\"staged\":%d}',jobdone,staged)")
  # Observe safe invalidation writes themselves,not just the absence of ACK.
  lua=once(lua,'local at=1;local reads=0;', 'local abortblank=false;local abortHDMA=false;local at=1;local reads=0;')
  lua=once(lua,'local function note(op,a,v)', 'local function note(op,a,v)if op==1 and a==0x2100 and v==0x80 then abortblank=true end;if op==1 and a==0x420c and v==0 then abortHDMA=true end;')
  lua=once(lua,"assert(STOP and v==0xee and ("+expect+"));", "assert(STOP and v==0xee and ("+expect+") and abortblank and abortHDMA);")
  view=bytes.fromhex((BASE/'probes/nes-joint266/cpu01/expected-display.hex').read_text())
  if name=='cgram':
   lua=once(lua,'for i,b in ipairs(bytes(INITOAM))do', "for i,b in ipairs(bytes(INITMAP))do emu.write(0x6000+BANK*0x4000+i-1,b,emu.memType.snesVideoRam)end\nfor i,b in ipairs(bytes(INITOAM))do")
   lua=once(lua,'for _,a in ipairs({0x16500', "for i,b in ipairs(bytes(INITOAM))do emu.write(i-1,b,emu.memType.snesSpriteRam)end\nfor _,a in ipairs({0x16500")
   lua=once(lua,'local at=1;local reads=0;', "local cgbytes={};emu.addMemoryCallback(function(a,v)cgbytes[#cgbytes+1]=v end,emu.callbackType.write,0x2122)\nlocal at=1;local reads=0;")
   lua=once(lua,"  local out=assert(io.open(OUT..'/cpu-result.json','w'));", "  assert(#cgbytes==512);for i,b in ipairs(JOBS[1].payload)do assert(cgbytes[i]==b,'actualCGRAM byte')end\n  local out=assert(io.open(OUT..'/cpu-result.json','w'));")
  header='local OUT='+json.dumps(d.as_posix())+'\nlocal BANK=0\nlocal STOP='+str(stop).lower()+'\nlocal VIEW={'+','.join(map(str,view))+'}\n'
  header+='local LABELS={'+','.join(n+'='+str(v) for n,v in labels.items())+'}\nlocal JOBS={'+','.join('{typed='+str(j['typed']).lower()+',descriptor="'+j['descriptor']+'",data="'+j['data']+'",token='+str(j['token'])+',target='+str(j['target'])+'}' for j in jobs)+'}\n'
  target=prior if name=='cgram' else expected
  for n,data in [('INITMAP',prior[:4096]),('INITOAM',prior[4608:5152]),('EXPECTMAP',target[:4096]),('EXPECTOAM',target[4608:5152])]:header+='local '+n+'="'+data.hex()+'"\n'
  (d/'fixture.json').write_text(json.dumps(jobs,indent=2)+'\n');guarded="local oldassert=assert\nfunction assert(v,msg)if not v then local f=io.open(OUT..'/error.txt','a');f:write(tostring(msg)..'\\n'..debug.traceback());f:close();emu.stop(1)end;return oldassert(v,msg)end\n"+lua
  (d/'capture.lua').write_text(header+guarded,newline='\n');env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  with (d/'mesen.log').open('wb') as log:
   r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(d/'capture.lua'),str(d/'spool.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-1200:]
  result=json.loads((d/'cpu-result.json').read_text());assert result['passed'];result.update(name=name,ROM=sha(d/'spool.sfc'),events=sha(d/'events.csv'),body_bytes=body);rows.append(result);print(json.dumps(result),flush=True)
 (root/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,source=sha(Path(__file__)),scope=__doc__),indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
