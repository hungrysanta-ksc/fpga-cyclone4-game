# SPDX-License-Identifier: MIT
"""Deterministic private SMB3(J) shortcut; no persistent cheat or ROM patch."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROM_SHA,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['rom','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert sha(a.rom)==ROM_SHA and not a.out.exists() and str(a.out).isascii()
 a.out.mkdir(parents=True)
 lua=r'''local count=0
local OUT="OUTPATH"
local f=assert(io.open(OUT..'/writes.tsv','w'))
local states=assert(io.open(OUT..'/scene.tsv','w'))
local bankselect=0
local function watch(a,v)
 local s=emu.getState()
 if a==0x8000 then bankselect=v end
 if count==588 and s['ppu.scanline']==192 and a==0x8001 and bankselect%8==5 then
  local q=assert(io.open(OUT..'/bank-edge-state.txt','w'))
  local keys={};for k,_ in pairs(s)do keys[#keys+1]=k end;table.sort(keys)
  for _,k in ipairs(keys)do q:write(k..'='..tostring(s[k])..'\n')end;q:close()
  local z=assert(io.open(OUT..'/bank-edge-oam.bin','wb'))
  for i=0,255 do z:write(string.char(emu.read(i,emu.memType.nesSpriteRam)))end;z:close()
 end
 if count>=340 then f:write(string.format('%d %d %d %04x %02x\n',count,s['ppu.scanline'],s['ppu.cycle'],a,v))end
end
emu.addMemoryCallback(watch,emu.callbackType.write,0x8000,0xffff,emu.cpuType.nes,emu.memType.nesMemory)
emu.addMemoryCallback(watch,emu.callbackType.write,0x2000,0x2007,emu.cpuType.nes,emu.memType.nesMemory)
emu.addEventCallback(function()
 local start=(count>=30 and count<34) or (count>=90 and count<96)
 local a=(count>=360 and count<366) or (count>=550 and count<556)
 emu.setInput({start=start,a=a,Start=start,A=a},0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 count=count+1
 if count==350 then
  local h=assert(io.open(OUT..'/intervention.txt','w'))
  h:write(string.format('frame350 RAM0075 %02x ->60; RAM0079 %02x ->80; one shot; no later writes\n',emu.read(0x75,emu.memType.nesInternalRam),emu.read(0x79,emu.memType.nesInternalRam)));h:close()
  emu.write(0x75,0x60,emu.memType.nesInternalRam);emu.write(0x79,0x80,emu.memType.nesInternalRam)
 end
 states:write(string.format('%d %02x %02x %02x %02x %02x %02x\n',count,emu.read(0x75,emu.memType.nesInternalRam),emu.read(0x79,emu.memType.nesInternalRam),emu.read(0xe5,emu.memType.nesInternalRam),emu.read(0x70a,emu.memType.nesInternalRam),emu.read(0x408,emu.memType.nesInternalRam),emu.read(0x409,emu.memType.nesInternalRam)))
 if count==349 or count==355 or count==540 or count==650 or count==680 then
  local q=assert(io.open(OUT..'/frame-'..count..'.png','wb'));q:write(emu.takeScreenshot());q:close()
 end
 f:flush();states:flush()
 if count==680 then f:close();states:close();emu.stop(0)end
end,emu.eventType.endFrame)
'''.replace('OUTPATH',a.out.as_posix())
 (a.out/'capture.lua').write_text(lua,encoding='utf8')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'mesen.log').open('wb') as f:
  r=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.rom),'--timeout=120','--doNotSaveSettings','--enableStdout','--nes.port1.type=NesController','--debug.scriptWindow.allowIoOsAccess=true'],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=150)
 assert r.returncode==0,(a.out/'mesen.log').read_text(errors='replace')
 assert len((a.out/'scene.tsv').read_text().splitlines())==680
 assert 'RAM0075 40' in (a.out/'intervention.txt').read_text(), 'Did not reach World 1; input/configuration failed'
 result=dict(completed=True,rom_sha256=ROM_SHA,mesen_sha256=sha(a.mesen),scope=__doc__,
  files={q.name:sha(q) for q in a.out.iterdir() if q.is_file()},scene_visual_confirmation_required=True)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS reference698 680 frames')

if __name__=='__main__':main()
