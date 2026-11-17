"""Isolate the real 65816 consumer with recorded queue arrivals and tile bytes."""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from analyze_nes_section841 import folder
from nes_tile842 import TEMP
import nes_handoff843 as handoff


def run(phase, test):
    src=folder(phase,"842controlfixed")
    dst=TEMP/f"nes-handoff843-{test}{'-v3' if test in ('stop','tailstop','preempt') else ''}-p{phase}"
    dst.mkdir(exist_ok=False)
    for pattern in ("client.sfc","expected-*.bin","map-*.bin","colors636-*.bin"):
        for file in src.glob(pattern):
            shutil.copyfile(file,dst/file.name)
    records=[json.loads(row) for row in (src/"packets.jsonl").read_text().splitlines()]
    data=json.loads(Path("analysis/tile842-results.json").read_text())["phases"][str(phase)]["control"]
    transfer,=[v for v in data["DMA_in_51"] if v["bytes"]==768]
    start51=json.loads(Path("analysis/section841-results.json").read_text())["phases"][str(phase)]["VB51_start"]
    gen=lambda b:int.from_bytes(b[8:10],"little")
    first=next(i for i,r in enumerate(records) if gen(bytes.fromhex(r[2]))==910)
    if test!="original":
        i=next(i for i in range(first,len(records)) if bytes.fromhex(records[i][2])[:2]==bytes([7,0]))
        bg=records.pop(i)
        assert bytes.fromhex(bg[3])==bytes(16)
        # Availability is at the receiving queue; the coupled ARM run separately charges the SPI time.
        ticks={"before":start51-20000,"inflight":transfer["start"][0]+8,
               "return":transfer["end"][0]+8,"stop":transfer["end"][0]+8,
               "tail":start51-20000,"tailstop":start51-20000,"preempt":start51-20000}
        bg[1]=ticks[test]
        records.append(bg)
        records.sort(key=lambda r:r[1])
        for i in range(first,len(records)):
            b=bytearray.fromhex(records[i][2])
            assert gen(b)==910
            b[2:4]=(i-first).to_bytes(2,"little")
            records[i][2]=b.hex()
    (dst/"arrivals.txt").write_text("".join(f"{r[1]} {r[2]} {r[3]}\n" for r in records))
    lua=(src/"capture.lua").read_text(encoding="utf8")
    tail=test in ("tail","tailstop","preempt")
    if tail:
        old=(handoff.prior.CLIENT/"body.bin").read_bytes()
        new=(handoff.CLIENT/"body.bin").read_bytes()
        writes=[f"emu.write({8192+i},{v},emu.memType.snesWorkRam)"
                for i,v in enumerate(new) if i>=len(old) or old[i]!=v]
        lua=lua.replace("  lastStatus=ack[1];","  if pw(8)==909 and pb(0)==3 and ack[1]==1 then\n"+
                        "\n".join(writes)+"\n  end\n  lastStatus=ack[1];",1)
        lua=handoff.bg_oracle(lua)
    lua=re.sub(r'local ROOT=.*',lambda _: "local ROOT="+json.dumps(dst.as_posix()),lua,count=1)
    a=lua.index("local cmds=assert")
    b=lua.index("local progressLog=",a)
    # PUSH target clocks come from the pipe transcript; never offer a fifth unretired head.
    lua=lua[:a]+"""local arrivals=assert(io.open(ROOT..'/arrivals.txt','r'))
local tick,bytes,payload
local function advance843()
 local line=arrivals:read('*l')
 if line then
  local t;t,bytes,payload=line:match('^(%d+) (%x+) (%x*)$');tick=assert(tonumber(t))
 else tick=nil;TOTAL=sent;finished=true end
end
advance843()
rpc=function()
 if stopped843 then return end
 local now=emu.getState().masterClock
 while tick and now>=tick do
  assert(sent-retired<4,'queue overflow');sent=sent+1
  requests[sent]=unhex(bytes);tilePayload[sent]=unhex(payload)
  local g=requests[sent]:byte(9)+256*requests[sent]:byte(10)
  frames[sent]=g-905;frameRelease[g-905]=frameRelease[g-905] or tick
  if requests[sent]:byte(1)==3 then sealIndex[g-905]=sent end
  advance843()
 end
end
""" + lua[b:]
    # Observe bus checks without advancing the emulated clock.
    mark="local function loaded()"
    lua=lua.replace(mark,"""local io843=assert(io.open(ROOT..'/io843.csv','w'))
local function observe843(a)
 local st=emu.getState()
 if word(0x1226)==910 and st.frameCount==51 and st['ppu.scanline']>=225 then
  io843:write(string.format('%d,%d,%d,%d,%d,%d\\n',st.masterClock,st['ppu.scanline'],a,index,sent,packet and pb(0) or -1))
 end
end
"""+mark,1)
    lua=lua.replace("if a==0x6001 then","if a==0x6001 then observe843(a);",1)
    lua=lua.replace("if a==0x6000 then rpc();","if a==0x6000 then rpc();observe843(a);",1)
    if test=="preempt":
        lua=lua.replace("rpc();observe843(a);","""if selectedBG843 and not preempt843 then
   preempt843=emu.getState().masterClock
   assert(sent==retired and index==sent+1 and unhex(bytes):byte(2)==2)
   tick=preempt843
   local f=assert(io.open(ROOT..'/preempt843.txt','w'));f:write(preempt843);f:close()
  end;rpc();observe843(a);""",1)
    lua=lua.replace("assert(captured==commits)","assert(captured==commits);io843:close()",1)
    if test in ("stop","tailstop"):
        endmap=transfer["end"][0]
        condition=(f"emu.getState().masterClock>{endmap}" if test=="stop" else "selectedBG843")
        head=("requests[index]:byte(1)==7" if test=="stop" else "sent==retired")
        lua=lua.replace("if a==0x6001 then observe843(a);",f"""if a==0x6001 then observe843(a);
  if word(0x1226)==910 and {condition} and not stopped843 then
   assert(commits==5 and not packet and {head})
   stopped843=emu.getState().masterClock;return 128
  end""",1)
        labels=json.loads((Path(__file__).resolve().parents[2]/"probes/nes-section841/client-paired-stop/labels.json").read_bytes())
        hook="""local function cancel843()
 if stopped843 and not canceled843 and word(0x1236)==1 then
  canceled843=true
  assert(commits==5)
  for addr=0x14d0,0x14d8,2 do assert(word(addr)==0) end
  local f=assert(io.open(ROOT..'/cancel843.txt','w'));f:write(stopped843..' '..emu.getState().masterClock);f:close()
  trace516:flush();io843:flush();emu.stop(0)
 end
end
"""
        lua=lua.replace("local function loaded()",hook+
                        f"checkedMem527(cancel843,emu.callbackType.exec,{labels['stop523']})\n"+
                        f"checkedMem527(cancel843,emu.callbackType.exec,{labels['service_done']})\nlocal function loaded()",1)
    (dst/"capture.lua").write_text(lua,encoding="utf8")
    args=[str(TEMP/"nes-bonus698-mesen/Mesen.exe"),"--testRunner",str(dst/"capture.lua"),str(dst/"client.sfc"),
          "--timeout=600","--doNotSaveSettings","--enableStdout","--snes.disableFrameSkipping=true",
          "--debug.scriptWindow.allowIoOsAccess=true","--debug.scriptWindow.scriptTimeout=90"]
    with (dst/"mesen.log").open("wb") as log:
        subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600,
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"))
    assert not (dst/"callback-error.txt").exists() and not (dst/"map-error.txt").exists()
    if test in ("stop","tailstop"):
        t,u=map(int,(dst/"cancel843.txt").read_text().split())
        assert endmap<t<=u
        from analyze_nes_section841 import window
        assert not any(r["clock"]>=t and r["event"] in ("ppu_dma","ppu_last","reveal","ack") for r in window(dst))
        return
    result=json.loads((dst/"result.json").read_bytes())
    assert result["passed"] and result["commits"]==6 and result["last_status"]==1
    for g in range(905,911):
        assert (dst/f"frame-{g}.rgb").read_bytes()==(src/f"frame-{g}.rgb").read_bytes()
    if test=='preempt':
        assert (dst/'preempt843.txt').is_file()
    if test=="original":
        assert (dst/"window.csv").read_bytes()==(src/"window.csv").read_bytes()


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("test",choices=("original","before","inflight","return","stop","tail","tailstop","preempt"))
    p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args()
    run(a.phase,a.test)
