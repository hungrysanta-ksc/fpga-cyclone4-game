"""Independently exercise the exact linked 65816 job routine with corrupted descriptors."""
import argparse,json,os,struct,subprocess
from pathlib import Path
from nes_bg659_client import job_code

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    body=(a.client/"body.bin").read_bytes()
    routine=job_code(0x3680);assert body[-len(routine):]==routine
    payload=bytes.fromhex(json.loads(a.jobs.read_bytes())["954/123"])
    game=a.game.read_bytes()[-131072:]
    addr=int.from_bytes(payload[:2],"little")+(payload[2]-80)*65536
    expected=bytes(game[(i&~15)+(i%2)*8+i%16//2] for i in range(addr,addr+16))
    for case in ("good","generation","slot","inverse","stop"):
        folder=a.out/case;folder.mkdir();desc=bytearray(payload)
        if case=="generation":desc[6]^=1
        if case=="slot":desc[8]^=1
        if case=="inverse":desc[4]^=1
        rom=bytearray((a.client/"sink165.sfc").read_bytes());code=bytearray()
        def emit(*bs):code.extend(bs)
        emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b)
        # Copy the already linked bytes directly to their original PBR.
        emit(0xa9,*struct.pack("<H",len(routine)-1),0xa2,0,0x90,0xa0,0x80,0x36,0x54,0x7e,0)
        emit(0xe2,0x20,0xa9,0,0x48,0xab)
        for j,b in enumerate([0x20,0x80,0x36,0x6b]):
            emit(0xa9,b,0x8f,j,0x3f,0x7e)
        for j,b in enumerate(desc):
            k=123*16+j;emit(0xa9,b,0x8f,k&255,k>>8,0x7f)
        def store8(reg,v):emit(0xa9,v,0x8d,reg&255,reg>>8)
        for k,v in ((0x1226,0xba),(0x1227,3),(0x2100,0x80),(0x2115,0x80),(0x2116,0),(0x2117,0x10),(0x4300,1),(0x4301,0x18),
                    (0x4302,0xb0),(0x4303,7),(0x4304,0x7f),(0x4305,16),(0x4306,0)):store8(k,v)
        emit(0xad,0x12,0x42,0x10,0xfb,0xa9,1,0x22,0,0x3f,0x7e,0x8f,1,0x60,0x5f,0x80,0xfe)
        rom[:len(code)]=code;rom[0x1000:0x1000+len(routine)]=routine
        (folder/"job.sfc").write_bytes(rom)
        lua="""local reads=0;local primed=false;local pos=0;local data={DATA}
local function result(s)
 local f=assert(io.open(PATH,'w'));f:write(s,' ',reads);f:close();emu.stop()
end
emu.addMemoryCallback(function()return 1 end,emu.callbackType.read,0x540000)
emu.addMemoryCallback(function()primed=true end,emu.callbackType.write,0x520000,0x53ffff)
emu.addMemoryCallback(function()if STOP and reads>0 then return 128 end;return reads==16 and 2 or (primed and 1 or 0)end,emu.callbackType.read,0x520000,0x53ffff)
emu.addMemoryCallback(function(a)if a~=BASE+reads then result('address_error')end;reads=reads+1;return data[reads]end,emu.callbackType.read,0x500000,0x51ffff)
emu.addMemoryCallback(function()result('reject')end,emu.callbackType.write,0x546000)
emu.addMemoryCallback(function()for i=1,16 do if emu.read(0x2000+i-1,emu.memType.snesVideoRam)~=data[i]then result('vram_error');return end end;result('return')end,emu.callbackType.write,0x5f6001)
"""
        result=folder/"result.txt"
        lua=lua.replace("DATA",",".join(map(str,expected))).replace("PATH",json.dumps(result.resolve().as_posix())).replace("BASE",str(0x500000+addr)).replace("STOP",str(case=="stop").lower())
        (folder/"job.lua").write_text(lua,encoding="utf-8")
        env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet")
        with (folder/"mesen.log").open("wb") as log:
            subprocess.run([str(a.mesen),"--testRunner",str((folder/"job.lua").resolve()),str((folder/"job.sfc").resolve()),"--timeout=15","--doNotSaveSettings","--debug.scriptWindow.allowIoOsAccess=true"],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.read_text()==("return 16" if case=="good" else "reject 16" if case=="stop" else "reject 0"),case

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("mesen","client","jobs","game","out"):p.add_argument("--"+n,type=Path,required=True)
    run(p.parse_args())
