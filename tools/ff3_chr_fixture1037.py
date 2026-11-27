"""Export a real FF3 CHR transition into a temporary test directory (no ROM redistribution)."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

from check_ff3_state_reference import DIGEST

def generate(work):
    rom = next(p for p in (Path.home()/"Downloads/test").glob("Final Fantasy III*.nes")
               if hashlib.sha256(p.read_bytes()).hexdigest()==DIGEST)
    image=work/"ff3.nes"
    shutil.copyfile(rom,image)
    script=work/"fixture.lua"
    script.write_text("OUT="+json.dumps((work/"transition.hex").as_posix())+"""
local mem=emu.memType.nesChrRam
local old={}
local frame=0
local transition=false
local first_picture=false
emu.addEventCallback(function()
    frame=frame+1
    if not first_picture then
        local pixels=emu.getScreenBuffer()
        for i=2,#pixels do
            if pixels[i]~=pixels[1] then
                first_picture=frame
                break
            end
        end
    end
    if transition and first_picture then
        local info=assert(io.open(OUT..'.time','w'))
        info:write(first_picture)
        info:close()
        emu.stop(0)
        return
    end
    local now={}
    for i=0,8191 do now[i]=emu.read(i,mem) end
    for tile=0,511 do
        local base=tile*16
        local changed=false
        local nonzero=0
        for i=base,base+15 do
            if now[i]~=old[i] then changed=true end
            if now[i]~=0 then nonzero=nonzero+1 end
        end
        if not transition and old[0] and changed and nonzero>=4 then
            local file=assert(io.open(OUT,'w'))
            file:write(string.format('%04x %04x\\n',tile,frame))
            for _,sample in ipairs({old,now}) do
                for i=base,base+15 do file:write(string.format('%02x\\n',sample[i])) end
            end
            file:close()
            transition=true
            break
        end
    end
    old=now
    if frame>=600 then emu.stop(1) end
end,emu.eventType.endFrame)
""",encoding="utf8")
    exe=Path("C:/works/emucap/adapters/mesen2/work/mesen/bin/win-x64/Release/Mesen.exe")
    subprocess.run([exe,"--testRunner",script,image,"--timeout=120","--doNotSaveSettings",
                    "--preferences.overrideSaveDataFolder=true",f"--preferences.saveDataFolder={work}",
                    "--debug.scriptWindow.allowIoOsAccess=true"],cwd=work,check=True,timeout=145,
                   env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                   creationflags=subprocess.CREATE_NO_WINDOW)
    data=[int(x,16) for x in (work/"transition.hex").read_text().split()]
    assert len(data)==34 and 0<=data[0]<512 and data[2:18]!=data[18:]
    first=int((work/"transition.hex.time").read_text())
    print(f"FF3 source transition on frame {data[1]}, CHR tile {data[0]}; first multicolor frame {first}")

if __name__=="__main__":
    with tempfile.TemporaryDirectory(prefix="nes-chr-reference-") as temp:
        private=Path(temp)
        generate(private)
        shutil.copyfile(private/"transition.hex",Path(sys.argv[1])/"transition.hex")
