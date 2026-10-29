# SPDX-License-Identifier: MIT
"""Check self-generated NES test in isolated Mesen, not SNES hardware."""
import argparse,json,os,subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--mesen',type=Path,default=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe'));a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
lua=r'''local out=assert(io.open(OUT..'/frames.tsv','w'))
local trace=assert(io.open(OUT..'/controller.tsv','w'))
local inputs={a=false,b=false,start=false,select=false,up=false,down=false,left=false,right=false}
emu.addEventCallback(function() inputs.a=emu.getState().frameCount>=80;emu.setInput(inputs,0) end,emu.eventType.endFrame)
-- Explicit injected serial bit: validates ROM behavior, not an actual pad.
emu.addMemoryCallback(function(a,v) local n=emu.getState().frameCount;local x=n>=80 and 0x41 or 0x40;if n>=79 and n<=83 then trace:write(string.format('%d\t%d\t%d\n',n,v,x));trace:flush() end;return x end,emu.callbackType.read,0x4016,0x4016,emu.cpuType.nes)
emu.addEventCallback(function()
 local s=emu.getState();local n=s.frameCount
 if n==60 or n==100 then
  local keys=assert(io.open(OUT..'/input-'..n..'.txt','w'));for p=0,4 do for k,v in pairs(emu.getInput(p)) do keys:write(tostring(p)..':'..tostring(k)..'='..tostring(v)..'\n') end end;keys:close()
  local detail=assert(io.open(OUT..'/state-'..n..'.txt','w'));for k,v in pairs(s) do detail:write(tostring(k)..'='..tostring(v)..'\n') end;detail:close()
  local size=emu.getScreenSize();assert(size.width==256 and size.height==240)
  local buf=emu.getScreenBuffer();local colors={};local count=0
  for y=16,223 do for x=16,239 do local c=buf[y*256+x+1];if not colors[c] then colors[c]=true;count=count+1 end end end
  out:write(string.format('%d\t%d\t%d\t%d\t%d\n',n,emu.read(1,emu.memType.nesPaletteRam),emu.read(0,emu.memType.nesNametableRam),count,buf[80*256+81]));out:flush()
 end
 if n==105 then out:close();trace:close();emu.stop(0) end
end,emu.eventType.endFrame)
'''
(d/'test.lua').write_text('local OUT='+json.dumps(d.as_posix())+'\n'+lua,newline='\n')
exe=a.mesen.resolve();assert exe.is_file()
env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
with (d/'mesen.log').open('wb') as f:r=subprocess.run([str(exe),'--testRunner',str(d/'test.lua'),str(a.rom.resolve()),'--timeout=30','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true','--nes.port1.type=9','--nes.autoConfigureInput=false'],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-5000:]
rows=[list(map(int,line.split('\t'))) for line in (d/'frames.tsv').read_text().splitlines()]
assert len(rows)==2 and rows[0][0]==60 and rows[1][0]==100 and rows[0][1]==0x21 and rows[1][1]==0x16,rows
assert rows[0][2]==rows[1][2]==1 and rows[0][3]>=2 and rows[1][3]>=2 and rows[0][4]!=rows[1][4],rows
res={'passed':True,'rom_sha256':sha(a.rom),'frames':rows,'scope':'Mesen NES display and injected 4016 serial-bit behavioral test; real controller, FPGA/SNES/hardware and audio not tested'}
(d/'result.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res))
