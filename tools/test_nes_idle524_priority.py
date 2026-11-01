# SPDX-License-Identifier: MIT
"""Hold the next real head until the last arbitration check or the first PPU write."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from nes_raw506 import once, sha
import nes_prefix523 as prefix
from nes_idle524 import arbitrate, packet
from test_nes_prefix523_edges import pace_beam
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE


PRIORITY = """
local CASE=@CASE@
local pacedLine=@PACED@
if pacedLine>=0 then
 local observed,first=-1,0
 emu.addMemoryCallback(function()
  local st=emu.getState();local line=st['ppu.scanline']
  if observed~=line then observed=line;first=st.masterClock end
  return line==pacedLine and st.masterClock-first>=900 and 1 or 0
 end,emu.callbackType.read,0x605f)
end
if CASE=='cold' then
 local vram=file('initial-vram.bin');local state=file('initial-state.bin')
 for i=1,#vram do emu.write(i-1,vram:byte(i),emu.memType.snesVideoRam) end
 for i=1,#state do emu.write(0xfff+i,state:byte(i),emu.memType.snesWorkRam) end
end
local held,initial,owner=nil,nil,nil
local armed,released,stopping,quiet=false,false,false,false
local targetedGrant,lastWrite,headACK,mid=false,false,false,false
local startLine,endLine=-1,-1
local grantClock,firstClock,lastClock,headClock,quietClock,issuedSize=0,0,0,0,0,0
local function tick()return emu.getState().masterClock end
local function activeImage()
 local b=word(0x1032);local bytes={}
 for _,range in ipairs({{b==0 and 0 or 0xc000,16384},{b==0 and 0x4000 or 0x8000,6144},{b==0 and 0x6000 or 0xa000,4096}}) do
  for i=0,range[2]-1 do bytes[#bytes+1]=string.char(emu.read(range[1]+i,emu.memType.snesVideoRam)) end
 end
 return table.concat(bytes)
end
emu.addMemoryCallback(function()
 if index==held and not armed then
  armed=true
  if CASE=='head' or CASE=='both' then released=true end
  if CASE=='stop' or CASE=='both' then stopping=true end
 end
end,emu.callbackType.exec,@PRIORITY@)
emu.addMemoryCallback(function()
 if index==held then
  assert(armed and not released and not packet and not stopping,'head/STOP lost priority')
  targetedGrant=true;grantClock=tick();issuedSize=word(0x4004+initial)
 end
end,emu.callbackType.exec,@GRANT@)
emu.addMemoryCallback(function() if stopping and not quiet then quiet=true;quietClock=tick() end end,emu.callbackType.exec,@QUIET@)
"""


def case(a,g,name,client=None,line=-1,edit_fixture=None):
    client=client or a.client
    folder=a.out/(f"{g}-{name}" + (f"-line{line}" if line>=0 else ""))
    folder.mkdir()
    records=[]
    bulk=0
    for record in (a.trace/"packets.jsonl").read_text().splitlines():
        _,_,body,tile=json.loads(record)
        b=bytes.fromhex(body)
        if int.from_bytes(b[8:10],"little")>g:
            break
        if name=="max_late_stop" and b[0]==7 and int.from_bytes(b[8:10],"little")==g and bulk<2:
            bulk+=1
            assert b[1]==0
            b=bytearray(b)
            offset,data=(0,bytes(range(256))*8) if bulk==1 else (2080,bytes(range(16)))
            struct.pack_into("<H",b,10,offset)
            struct.pack_into("<H",b,14,len(data))
            tile=data.hex()
        records.append(b)
        if tile:
            (folder/f"tile-{len(records):04d}.bin").write_bytes(bytes.fromhex(tile))
    (folder/"requests.bin").write_bytes(b"".join(struct.pack("<H",len(b))+b for b in records))
    for gen in range(905,g+1):
        for stem in ("map","expected"):
            shutil.copyfile(a.trace/f"{stem}-{gen}.bin",folder/f"{stem}-{gen}.bin")
    shutil.copyfile(client/"sink165.sfc",folder/"client.sfc")
    if name=="cold":
        for stem in ("state","vram"):
            shutil.copyfile(a.out/f"{g}-late_stop"/f"{stem}.bin",folder/f"initial-{stem}.bin")
    labels=json.loads((client/"labels.json").read_text())
    s=once(LUA,"local function loaded()",PRIORITY+"""
local function loaded()
 if CASE~='cold' and not packet and not held and word(0x1228)==1 and word(0x1226)==FAULT and word(0x1252)+8<word(0x1250) then
  held=index;initial=word(0x1252);owner=activeImage()
 end
 if held==index and not released then return end""")
    # Inject after the real 6000 empty read. The head is made visible at
    # precisely the chosen arbitration point, independently of fixture pacing.
    s=once(s,"if st.masterClock<ready[index]then return end","if index~=held and st.masterClock<ready[index]then return end")
    s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if stopping then return 128 end")
    s=once(s,"   dmaRemaining=dmaRemaining-1","""   if targetedGrant and held==index and not packet then
    if dmaRemaining==dmaLength then
     mid=true;released=true;firstClock=tick();startLine=emu.getState()['ppu.scanline']
     if CASE=='late_stop' or CASE=='max_late_stop' then stopping=true end
    end
    if dmaRemaining==1 then lastWrite=true;lastClock=tick();endLine=emu.getState()['ppu.scanline'] end
   end
   dmaRemaining=dmaRemaining-1""")
    s=once(s,"  lastStatus=ack[1]","""  if index==held then
   assert(released and not stopping and ack[1]==0,'wrong head retirement')
   assert(word(0x1252)==initial+(targetedGrant and 8 or 0),'cursor at head ACK')
   headACK=true;headClock=tick()
  end
  lastStatus=ack[1]""")
    s=once(s,"   local hdma=file(",MAP_ORACLE+"   local hdma=file(")
    # Empty-queue STOP has no packet token to reject. Stop the fixture only
    # after the consumer is demonstrably quiet and previous screen is captured.
    s=once(s," if (rejected or index>TOTAL)", """ if quiet and captured==commits and st.frameCount>shown+2 then
  if CASE=='late_stop' then
   for _,m in ipairs({{'vram',0,65536,emu.memType.snesVideoRam},{'state',0x1000,0x500,emu.memType.snesWorkRam}}) do
    local dump={};for i=0,m[3]-1 do dump[#dump+1]=string.char(emu.read(m[2]+i,m[4])) end
    local f=assert(io.open(ROOT..'/'..m[1]..'.bin','wb'));f:write(table.concat(dump));f:close()
   end
  end
  assert(not packet and index==held and retired==held-1 and word(0x1236)==1)
  assert(word(0x1248)==FAULT-905 and word(0x124a)==0 and commits==FAULT-905)
  assert(owner==activeImage() and word(0x1252)==initial+(lastWrite and 8 or 0))
  local f=assert(io.open(ROOT..'/retained.rgb','wb'));local screen=emu.getScreenBuffer()
  for y=0,238 do local row={};for x=0,255 do local b=screen[y*256+x+1];row[#row+1]=string.char((b>>16)&255,(b>>8)&255,b&255) end;f:write(table.concat(row)) end;f:close()
 end
 if (quiet and captured==commits or rejected or index>TOTAL)""")
    s=once(s,"  assert(captured==commits)","""  assert(captured==commits and (CASE=='cold' or (armed and held)))
  assert(targetedGrant==(CASE=='late_head' or CASE=='late_stop' or CASE=='max_late_stop' or CASE=='bad_manifest'))
  assert(lastWrite==targetedGrant and mid==targetedGrant)
  assert(headACK==(CASE=='head' or CASE=='late_head' or CASE=='bad_manifest'))
  assert(quiet==(CASE=='stop' or CASE=='both' or CASE=='late_stop' or CASE=='max_late_stop'))
  assert(CASE~='max_late_stop' or issuedSize==2048,'maximum DMA missing')
  local f=assert(io.open(ROOT..'/race.txt','w'))
  f:write(string.format('%d %d %d %d %d %d %d %d',issuedSize,grantClock,firstClock,lastClock,headClock,quietClock,startLine,endLine));f:close()""")
    stops=name in ("stop","both","late_stop","max_late_stop")
    fields=dict(ROOT=json.dumps(folder.as_posix()),CASE=json.dumps(name),PACED=line,TOTAL=len(records),
                FRAMES=g-904-int(stops),SCHEDULE='"continuous"',START=3000000,FAULT=g,
                MODE=json.dumps("bad_version" if name=="bad_manifest" else "normal"),POISON='false',COMPACT='true',PRIORITY=labels['priority524'],
                GRANT=labels['grant524'],QUIET=labels['quiet'])
    if edit_fixture:
        s=edit_fixture(s,labels)
    for key,value in fields.items():
        s=s.replace("@"+key+"@",str(value))
    s=s.replace('emu.addMemoryCallback(', 'memory524(').replace('emu.addEventCallback(', 'event524(')
    s=once(s,"local function file(name)","""local function checked(callback)
 return function(...)
  local ok,v=pcall(callback,...)
  if not ok then local f=assert(io.open(ROOT..'/error.txt','w'));f:write(tostring(v));f:close();emu.stop(1);return end
  return v
 end
end
local function memory524(cb,...)return emu.addMemoryCallback(checked(cb),...)end
local function event524(cb,...)return emu.addEventCallback(checked(cb),...)end
local function file(name)""")
    (folder/"capture.lua").write_text(s,encoding="utf8",newline="\n")
    with (folder/"mesen.log").open("wb") as log:
        subprocess.run([str(a.mesen),"--testRunner",str(folder/"capture.lua"),str(folder/"client.sfc"),
                        "--timeout=120","--doNotSaveSettings","--enableStdout","--snes.disableFrameSkipping=true",
                        "--debug.scriptWindow.allowIoOsAccess=true","--debug.scriptWindow.scriptTimeout=90"],
                       cwd=folder,env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                       stdout=log,stderr=subprocess.STDOUT,timeout=135,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    r=json.loads((folder/"result.json").read_text())
    assert r["passed"] and r["commits"]==fields["FRAMES"]-int(name=="bad_manifest")
    if name=="bad_manifest":
        assert r["last_status"]==224
    for gen in range(905,905+r["commits"]):
        assert sha(folder/f"frame-{gen}.rgb")==sha(a.trace/f"frame-{gen}.rgb")
    if stops or name=="bad_manifest":
        assert sha(folder/"retained.rgb")==sha(a.trace/f"frame-{g-1}.rgb")
    size,grant,first,last,ack,quiet,start_line,end_line=map(int,(folder/"race.txt").read_text().split())
    if grant:
        assert grant < first <= last and max(ack,quiet)>last
        assert 225<=start_line<=end_line<262
        if line>=0:
            assert line<=start_line<=line+2
    return dict(generation=g,case=name,commits=r["commits"],size=size,grant=grant,first_write=first,
                last_write=last,next_head_ACK=ack,quiet=quiet,start_line=start_line,end_line=end_line)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('mesen','client','trace','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    results=[]
    for g in (906,907):
        for name in ('head','stop','both','late_head','late_stop','bad_manifest','cold'):
            results.append(case(a,g,name))
            print(results[-1],flush=True)
    results.append(case(a,906,"max_late_stop"))
    paced=a.out/'paced-client'
    prefix.build(paced,emitter=lambda c:prefix.emit(c,before_beam=pace_beam,before_start=arbitrate),
                 fill=True,packet_edit=packet,upload_edit=prefix.upload)
    edge=case(a,906,"max_late_stop",client=paced,line=232)
    (a.out/'line232.json').write_text(json.dumps(edge,indent=2)+'\n',newline='\n')
    (a.out/'priority.json').write_text(json.dumps(results,indent=2)+'\n',newline='\n')
