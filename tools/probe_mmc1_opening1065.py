"""Sample Zelda II's unmodified title-screen PPU writes and frame colors."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zlib
from probe_mmc1_1063 import MESEN, ROOT

OUT = ROOT.parent/"probes/nes-mmc1-1065"

def main():
    out = OUT
    out.mkdir(parents=True,exist_ok=True)
    rom = Path.home()/"Downloads/test/Zelda no Densetsu 2 (K).nes"
    assert zlib.crc32(rom.read_bytes())==0x5696ba15
    with tempfile.TemporaryDirectory(prefix="zelda2-title-") as d:
        d=Path(d)
        lua = """
local f=assert(io.open(@OUT@,"w"))
local frame=0
local function write(a,v,kind)
 if frame%60~=0 and frame~=119 then return end
 local s=emu.getState()
 f:write(string.format("%d %d %d %s %04x %02x\\n",frame,s["ppu.scanline"],s["ppu.cycle"],kind,a,v))
end
emu.addMemoryCallback(function(a,v) write(a,v,"CPU") end,emu.callbackType.write,0x2000,0x2007)
emu.addMemoryCallback(function(a,v) write(a,v,"CHR") end,emu.callbackType.write,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
emu.addEventCallback(function()
 if frame%60==0 or frame==119 then
  if frame==60 then
  for i=0,8191 do f:write(string.format("PATTERN %d %02x\\n",i,emu.read(i,emu.memType.nesChrRam))) end
 end
 local pic=emu.getScreenBuffer()
  local colors={} for _,p in ipairs(pic) do colors[p]=true end
  local n=0 for _ in pairs(colors) do n=n+1 end
  f:write(string.format("FRAME %d COLORS %d\\n",frame,n))
 end
 frame=frame+1
 if frame==1201 then f:close();emu.stop(0) end
end,emu.eventType.endFrame)
"""
        script=d/"trace.lua"
        script.write_text(lua.replace("@OUT@",json.dumps((d/"events.txt").as_posix())))
        with (out/"mesen.log").open("wb") as log:
            subprocess.run([MESEN,"--testRunner",script,rom,"--timeout=150","--doNotSaveSettings",
                "--debug.scriptWindow.allowIoOsAccess=true","--preferences.overrideSaveDataFolder=true",
                "--preferences.saveDataFolder="+str(d)],cwd=d,env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",
                DOTNET_ROOT_X64="C:/works/dotnet"),stdout=log,stderr=subprocess.STDOUT,check=True,
                timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)

        (out/"zelda2-opening.txt").write_bytes((d/"events.txt").read_bytes())

if __name__=="__main__": main()
