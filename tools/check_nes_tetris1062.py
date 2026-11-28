"""Compare CNROM latch behavior on actual CPU writes from the supplied Tetris."""
import json
import os
import subprocess
import tempfile
import zlib
from pathlib import Path
from prepare_nes_compat1062 import OUT

def run():
    raw=(Path.home()/"Downloads/test/Tetris (j).nes").read_bytes()
    assert zlib.crc32(raw)==0x6118313f
    reports=[]
    runner=Path("C:/works/emucap/adapters/mesen2/work/mesen/bin/win-x64/Release/Mesen.exe")
    for sub in (1,2):
        with tempfile.TemporaryDirectory(prefix="cnrom-") as tmp:
            work=Path(tmp)
            header=bytearray(raw[:16])
            header[6:9]=bytes((0x31,8,sub<<4))
            (work/"cart.nes").write_bytes(header+raw[16:])
            dump=work/"banks.txt"
            (work/"game.lua").write_text("local out=assert(io.open("+json.dumps(dump.as_posix())+",'w'))\n"+"""
local frame=0
local watch=nil
local function fetch(addr)
 out:write(string.format("D %d %04x\\n",frame,addr))
end
emu.addMemoryCallback(function(addr,value)
 local prg=emu.read(addr-0x8000,emu.memType.nesPrgRom)
 if (value & 3) ~= (value & prg & 3) then
  if not watch then watch=emu.addMemoryCallback(fetch,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory) end
 elseif watch then
  emu.removeMemoryCallback(watch,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
  watch=nil
 end
 out:write(string.format("W %d %04x %d %d\\n",frame,addr,value,prg))
end,emu.callbackType.write,0x8000,0xffff)
emu.addEventCallback(function()
 emu.setInput({start=frame>=190 and frame%160<4 and frame<900,
 a=frame%100<5,right=frame%130<12,down=frame>900 and frame%145<85},0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 if frame%30==0 then
  local pic=emu.getScreenBuffer()
  local h=0
  for i=1,#pic do h=(h*33+pic[i]) & 0xffffffff end
  out:write(string.format("P %d %08x\\n",frame,h))
 end
 frame=frame+1
 if frame==5400 then out:close();emu.stop(0) end
end,emu.eventType.endFrame)
""")
            with (OUT/f"tetris-{sub}.log").open("wb") as log:
                subprocess.run([runner,"--testRunner","--nes.disableGameDatabase=true","--nes.autoConfigureInput=false",
                    "--nes.port1.type=NesController",work/"game.lua",work/"cart.nes","--timeout=160","--doNotSaveSettings",
                    "--enableStdout","--debug.scriptWindow.allowIoOsAccess=true","--preferences.overrideSaveDataFolder=true",
                    "--preferences.saveDataFolder="+tmp],cwd=work,env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",
                    DOTNET_ROOT_X64="C:/works/dotnet"),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=190,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            reports.append(dump.read_text().splitlines())
    writes=[s.split() for s in reports[0] if s.startswith("W ")]
    pixels=[s.split()[-1] for s in reports[0] if s.startswith("P ")]
    # Retain per-write evidence outside of the distributed package.
    for i,rows in enumerate(reports):
        (OUT/f"tetris-{i+1}-events.txt").write_text("\n".join(rows))

    assert writes and len(pixels)==180 and len(set(pixels))>3
    divergent=[(frame,addr) for _,frame,addr,v,rom in writes if (int(v)&3)!=(int(v)&int(rom)&3)]
    assert divergent==[("0","8002")]
    assert not any(row.startswith("D ") for rows in reports for row in rows)
    assert reports[0]==reports[1]
    return dict(frames=5400, writes=len(writes), selected_banks=sorted({int(s[3])&3 for s in writes}),
                equal_picture_samples=len(pixels),different_pictures=len(set(pixels)),reset_latch_difference=divergent,chr_fetches_before_resync=0)

if __name__=="__main__":
    result=run()
    (OUT/"tetris.json").write_text(json.dumps(result,indent=2))
    print(result)
