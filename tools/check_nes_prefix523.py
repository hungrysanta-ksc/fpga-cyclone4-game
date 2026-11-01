# SPDX-License-Identifier: MIT
"""Fault after a real prefix write, retain display, and boot with the dirty memories."""
import argparse
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

from nes_raw506 import once, sha
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE

OBSERVER="""
local early523,armed523,active523,lastWrite523=0,false,nil,false
local tileBytes523={[0]={},[1]={}}
local function rememberTile523()
 local bank=word(0x1034)
 local base=pb(1)==0 and (bank==0 and 0 or 0xc000) or (bank==0 and 0x4000 or 0x8000)
 for i=1,#tile do tileBytes523[bank][base+pw(10)+i-1]=tile:byte(i) end
end
local function checkTiles523()
 for addr,expected in pairs(tileBytes523[word(0x1032)]) do
  assert(emu.read(addr,emu.memType.snesVideoRam)==expected,'tile VRAM '..addr)
 end
end
local function memory523(address,n,kind)
 local b={}
 for i=0,n-1 do b[i+1]=string.char(emu.read(address+i,kind)) end
 return table.concat(b)
end
local function activeImage523()
 local b=word(0x1032)
 local m=emu.memType.snesVideoRam
 return memory523(b==0 and 0 or 0xc000,16384,m)..memory523(b==0 and 0x4000 or 0x8000,6144,m)..memory523(b==0 and 0x6000 or 0xa000,4096,m)
end
if MODE=='normal' then
 local data=file('initial-vram.bin')
 for i=1,#data do emu.write(i-1,data:byte(i),emu.memType.snesVideoRam) end
 local state=file('initial-state.bin')
 for i=1,#state do emu.write(0xfff+i,state:byte(i),emu.memType.snesWorkRam) end
end
emu.addMemoryCallback(function()
 if pw(8)==FAULT then armed523=true end
end,emu.callbackType.exec,@CHECK@)
emu.addMemoryCallback(function()
 if pw(8)==FAULT then early523=early523+1 end
 assert(word(0x1034)~=word(0x1032) and word(0x1252)+8<word(0x1250),'prefix owner')
end,emu.callbackType.exec,@ISSUE@)
"""


def trial(a,mode,g,client):
    folder=a.out/f"{mode}-{g}"
    folder.mkdir()
    packets=[]
    for line in (a.trace/"packets.jsonl").read_text().splitlines():
        _,_,body,tile=json.loads(line)
        b=bytes.fromhex(body)
        if int.from_bytes(b[8:10],"little")>g: break
        packets.append(b)
        if tile:(folder/f"tile-{len(packets):04d}.bin").write_bytes(bytes.fromhex(tile))
    (folder/"requests.bin").write_bytes(b"".join(struct.pack("<H",len(b))+b for b in packets))
    for gen in range(905,g+1):
        for stem in ("expected","map"):
            shutil.copyfile(a.trace/f"{stem}-{gen}.bin",folder/f"{stem}-{gen}.bin")
    if mode=="normal":
        dirty=a.out/f"after_prefix-{g}"
        for name in ("vram","state"):
            shutil.copyfile(dirty/f"{name}.bin",folder/f"initial-{name}.bin")
    shutil.copyfile(client/"sink165.sfc",folder/"client.sfc")
    labels=json.loads((client/"labels.json").read_text())
    s=once(LUA,"local function loaded()",OBSERVER+"\nlocal function loaded()")
    s=once(s,"   dmaRemaining=dmaRemaining-1","   if dmaRemaining==1 and early523>0 then lastWrite523=true end\n   dmaRemaining=dmaRemaining-1")
    s=once(s," if a==0x6001 then",""" if a==0x6001 then
  if MODE=='before_prefix' and armed523 or MODE=='after_prefix' and lastWrite523 then return 128 end""")
    s=once(s,"if pb(0)==7 then assert(lastStatus==0","if pb(0)==7 and lastStatus<0xe0 then assert(lastStatus==0")
    s=once(s,"   local hdma=file(",MAP_ORACLE+"   local hdma=file(")
    s=once(s,"  lastStatus=ack[1]","  lastStatus=ack[1];if pb(0)==7 and lastStatus==0 then rememberTile523() end")
    s=once(s,"   commits=commits+1","   checkTiles523();active523=activeImage523();commits=commits+1")
    s=once(s,"  if rejected then\n   local screen=", """  if rejected then
   assert(active523==activeImage523() and word(0x1248)==FAULT-905 and word(0x124a)==0,'visible history changed')
   assert((MODE=='before_prefix' and armed523 and early523==0) or (MODE~='before_prefix' and early523>0),'missing fault edge')
   assert(MODE~='after_prefix' or lastWrite523,'missing last PPU write before STOP')
   assert(word(0x1228)==2,'fault did not latch')
   for _,m in ipairs({{'vram',0,65536,emu.memType.snesVideoRam},{'state',0x1000,0x500,emu.memType.snesWorkRam}}) do
    local f=assert(io.open(ROOT..'/'..m[1]..'.bin','wb'));f:write(memory523(m[2],m[3],m[4]));f:close()
   end
   local screen=""")
    s=once(s,"  assert(captured==commits)","""  assert(captured==commits)
  local countFile=assert(io.open(ROOT..'/prefix-count.txt','w'));countFile:write(tostring(early523));countFile:close()""")
    for k,v in dict(ROOT=json.dumps(folder.as_posix()),MODE=json.dumps(mode),TOTAL=len(packets),SCHEDULE='"continuous"',
                    POISON='false',START=3000000,COMPACT='true',FAULT=g,FRAMES=g-904,
                    CHECK=labels["check523"],ISSUE=labels["issue523"]).items():
        s=s.replace("@"+k+"@",str(v))
    (folder/"capture.lua").write_text(s,encoding="utf8",newline="\n")
    with (folder/"mesen.log").open("wb") as log:
        subprocess.run([str(a.mesen),"--testRunner",str(folder/"capture.lua"),str(folder/"client.sfc"),"--timeout=120",
                        "--doNotSaveSettings","--enableStdout","--snes.disableFrameSkipping=true",
                        "--debug.scriptWindow.allowIoOsAccess=true","--debug.scriptWindow.scriptTimeout=90"],
                       cwd=folder,env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                       stdout=log,stderr=subprocess.STDOUT,timeout=135,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    r=json.loads((folder/"result.json").read_text())
    expected=g-904 if mode=="normal" else g-905
    assert r["passed"] and r["commits"]==expected
    assert r["last_status"]==({"normal":1,"bad_version":224}.get(mode,228))
    for gen in range(905,905+expected):
        assert sha(folder/f"frame-{gen}.rgb")==sha(a.trace/f"frame-{gen}.rgb")
    if mode!="normal":assert sha(folder/"retained.rgb")==sha(folder/f"frame-{g-1}.rgb")
    return dict(commits=expected,status=r["last_status"],prefixes_in_target=int((folder/"prefix-count.txt").read_text()))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("client","mesen","trace","out"):p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    results={}
    for g in (906,907):
        for mode in ("before_prefix","after_prefix","bad_version","normal"):
            results[f"{mode}-{g}"]=trial(a,mode,g,a.client)
            print(g,mode,results[f"{mode}-{g}"],flush=True)
    (a.out/"guards.json").write_text(json.dumps(results,indent=2)+"\n",newline="\n")
