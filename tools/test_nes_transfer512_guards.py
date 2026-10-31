# SPDX-License-Identifier: MIT
"""Exercise real 65816 map expansion, malformed streams and mid-expansion STOP."""
import argparse
import json
import os
import struct
import subprocess
from pathlib import Path
from analyze_nes_output511 import encode_linear
from nes_raw506 import sha

LUA = """
local folder=FOLDER
local function file(name)local f=assert(io.open(folder..'/'..name,'rb'));local s=f:read('*a');f:close();return s end
local packets={file('begin.bin'),file('map.bin')}
local expected=file('expected.bin')
local index=1
local ack={}
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
local function word(a)return rd(a)+256*rd(a+1)end
local armed=false
local observed=nil
emu.addMemoryCallback(function()
 if index==2 then armed=true end
end,emu.callbackType.exec,STOP_PC)
emu.addMemoryCallback(function(a,v)
 if a==0x6000 then
  if index==2 and not observed then observed=emu.getState().masterClock end
  return index<=2 and 1 or 0
 end
 if a==0x6001 then return STOP and armed and 128 or 0 end
 local n=packets[index] and #packets[index] or 0
 if a==0x6004 then return n&255 end
 if a==0x6005 then return n>>8 end
end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)
 local p=assert(packets[index]);local pos=a-0x400000+1
 assert(pos>=1 and pos<=#p,'packet overread');return p:byte(pos)
end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function(a,v)
 if a<0x601c then ack[a-0x6010]=v;return end
 assert(v==0xa5);local p=packets[index]
 for i=2,9 do assert(ack[i]==p:byte(i+1))end
 assert(ack[1]==p:byte(1) and ack[10]==0x65 and ack[11]==0x9a)
 if index==1 then assert(ack[0]==0);index=2;return end
 assert(ack[0]==STATUS,'unexpected ACK '..tostring(ack[0]))
 assert(word(0x1248)==0 and word(0x124a)==0,'unsealed display published')
 if STATUS==0 then
  local base=0x10000+word(0x1020)+0x5000+OFFSET
  for i=1,#expected do assert(rd(base+i-1)==expected:byte(i),'word '..i)end
 end
 local f=assert(io.open(folder..'/pass','w'));f:write(ack[0]);f:close();local timing=assert(io.open(folder..'/clocks','w'));timing:write(emu.getState().masterClock-observed);timing:close();index=3;emu.stop(0)
end,emu.callbackType.write,0x6010,0x601c)
emu.addEventCallback(function()assert(emu.getState().frameCount<30,'watchdog')end,emu.eventType.endFrame)
"""


def run(a):
    a.out.mkdir(parents=True, exist_ok=False)
    begin = struct.pack("<BBHIHHHH",1,0,0,1,905,0,12,0) + struct.pack("<HHII",0x4891,0,0,1)
    cases = []
    for n in (64,128,192):
        data = bytes(b for i in range(n//2) for b in (i if i < 8 else 77, 31 if i<24 else i))
        body = encode_linear(data[::2]) + encode_linear(data[1::2])
        cases.append((f"direct{n}",data,body,2,128,n,0,False))
        if a.pairs_only:
            cases.append((f"literal{n}",data,data,2,128,0,0,False))
    cases.extend([
        ("stop",data,body,2,128,n,0xe4,True),
        ("truncated",data,body[:-1],2,128,n,0xe0,False),
        ("trailer",data,body+b"\0",2,128,n,0xe0,False),
        ("run_over_plane",data,b"\xff\x11",2,128,n,0xe0,False),
        ("wrong_section",data,body,3,128,n,0xe0,False),
        ("unaligned",data,body,2,129,n,0xe0,False),
        ("bank_overflow",data,body,2,4096-64,n,0xe0,False),
        ("oversize",data,body,2,128,256,0xe0,False),
    ])
    labels=json.loads((a.client/"labels.json").read_text())
    if a.pairs_only:
        cases = [c for c in cases if c[0].startswith(("direct","literal"))]
    results = {}
    clocks = {}
    for name, expected, body, section, at, span, status, stop in cases:
        folder = a.out / name
        folder.mkdir()
        (folder/"begin.bin").write_bytes(begin)
        (folder/"map.bin").write_bytes(struct.pack("<BBHIHHHH",2 if name.startswith("literal") else 9,section,1,1,905,at,len(body),span)+body)
        (folder/"expected.bin").write_bytes(expected)
        lua = LUA.replace("FOLDER", json.dumps(folder.as_posix())).replace("STOP_PC",str(labels["map_run_done512"])).replace("STOP","true" if stop else "false").replace("STATUS",str(status)).replace("OFFSET",str(at))
        (folder/"guard.lua").write_text(lua)
        with (folder/"mesen.log").open("wb") as log:
            subprocess.run([str(a.mesen),"--testRunner",str(folder/"guard.lua"),str(a.client/"sink165.sfc"),"--timeout=30","--doNotSaveSettings","--enableStdout","--debug.scriptWindow.allowIoOsAccess=true"],env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=42,check=True)
        assert (folder/"pass").read_text()==str(status),name
        results[name]=status
        clocks[name]=int((folder/"clocks").read_text())
    (a.out/"result.json").write_text(json.dumps({"passed":True,"cases":results,"packet_clocks":clocks,"client_SHA256":sha(a.client/"sink165.sfc")},indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("mesen","out","client"):
        p.add_argument("--"+name,type=lambda s:Path(s).resolve(),required=True)
    p.add_argument("--pairs-only",action="store_true")
    run(p.parse_args())
