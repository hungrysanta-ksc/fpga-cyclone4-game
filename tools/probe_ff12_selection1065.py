"""Trace both menu choices in an isolated copy of the FF1&2 cartridge session."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from zlib import crc32
from probe_mmc1_1063 import MESEN
from prepare_sxrom1065 import OUT

def main():
    rom=Path.home()/"Downloads/test/Final Fantasy 1 & 2 (J) [!].nes"
    assert crc32(rom.read_bytes())==0x6f8906ad
    for choice in (1,2):
        with tempfile.TemporaryDirectory(prefix="ff12-menu-") as d:
            work=Path(d)
            lua="""
local f=assert(io.open(@OUT@,"w"))
local bus=assert(io.open(@BUS@,"w"))
local n=0
emu.addMemoryCallback(function(a,v)
 bus:write(string.format("0 %04x %02x %x\\n",a,v,emu.getState().masterClock))
end,emu.callbackType.write,0x8000,0xffff)
emu.addEventCallback(function()
 emu.setInput({down=(@CHOICE@==2 and n>=320 and n<326),a=(n>=360 and n<365) or (n>=450 and n<455),start=n>=400 and n<405},0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 n=n+1
 if n==180 or n==240 or n==630 then local image=assert(io.open(@PIC@..n..".png","wb"));image:write(emu.takeScreenshot());image:close() end
 if n%30==0 then
  local m=emu.convertAddress(0xfffc,emu.memType.nesMemory,emu.cpuType.nes)
  for a=0x8000,0xe000,0x2000 do
   local rom=emu.convertAddress(a,emu.memType.nesMemory,emu.cpuType.nes)
   bus:write(string.format("1 %04x %x\\n",a,rom.address))
  end
  local ram=emu.convertAddress(0x6123,emu.memType.nesMemory,emu.cpuType.nes)
  if ram and ram.memType==emu.memType.nesSaveRam then bus:write(string.format("4 6123 %x\\n",ram.address)) end
  local pix=emu.getScreenBuffer();local colors={};local hash=0
  for _,v in ipairs(pix) do colors[v]=true;hash=((hash*31)~v)&0xffffffff end
  local count=0;for _ in pairs(colors) do count=count+1 end
  f:write(string.format("%d %x %d %08x\\n",n,m.address,count,hash))
 end
 if n==720 then f:close();bus:close();emu.stop(0) end
end,emu.eventType.endFrame)
"""
            script=work/"probe.lua"
            script.write_text(lua.replace("@BUS@",json.dumps((work/"bus").as_posix())).replace("@OUT@",json.dumps((work/"rows.txt").as_posix())).replace("@CHOICE@",str(choice)).replace("@PIC@",json.dumps((work/"screen-").as_posix())))
            with (OUT/f"ff{choice}-mesen.log").open("wb") as log:
                subprocess.run([MESEN,"--testRunner",script,rom,"--timeout=120","--doNotSaveSettings",
                    "--nes.autoConfigureInput=false","--nes.port1.type=NesController",
                    "--debug.scriptWindow.allowIoOsAccess=true","--preferences.overrideSaveDataFolder=true",
                    "--preferences.saveDataFolder="+str(work)],env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                    cwd=work,stdout=log,stderr=subprocess.STDOUT,timeout=150,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            (OUT/f"ff{choice}.trace").write_bytes((work/"bus").read_bytes())
            for pic in work.glob("screen-*.png"):
                (OUT/f"ff{choice}-{pic.name}").write_bytes(pic.read_bytes())
            (OUT/f"ff{choice}-menu.txt").write_bytes((work/"rows.txt").read_bytes())

    for choice,expected in ((1,0x3fffc),(2,0x7fffc)):
        rows=(OUT/f"ff{choice}-menu.txt").read_text().splitlines()
        assert len(rows)==24 and int(rows[-1].split()[1],16)==expected
if __name__=="__main__":main()
