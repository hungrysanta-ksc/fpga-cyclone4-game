# SPDX-License-Identifier: MIT
"""Replay the pinned MMC520 packet arrivals; observe receipts, DMA registers and upload credit."""
import argparse
import csv
import json
import os
import shutil
import subprocess
from pathlib import Path

from nes_raw506 import once, sha
from test_nes_raw506_joint import lua_rpc
from test_nes_trim514_schedule import MAP_ORACLE
from test_nes_window516 import instrument

ROOT = Path(__file__).resolve().parents[1]

CLOCKED_INPUT = """
local input522=assert(io.open(ROOT..'/arrivals.tsv','r'))
local function next522()
 local row=assert(input522:read('*l'))
 local t,b,p=row:match('^(%d+)\t([^\t]+)\t(.*)$')
 return assert(tonumber(t)),b,p
end
local target522,b522,p522=next522()
local finished522=false
rpc=function()
 if finished522 then return end
 local now=emu.getState().masterClock
 while now>=target522 do
  if b522=='FINISH' then
   TOTAL=sent;finished522=true;input522:close();return
  end
  assert(sent-retired<4,'queue overflow')
  sent=sent+1
  requests[sent]=unhex(b522);tilePayload[sent]=unhex(p522)
  local g=requests[sent]:byte(9)+256*requests[sent]:byte(10)
  frames[sent]=g-905;frameRelease[g-905]=assert(sourceRelease[g])
  if requests[sent]:byte(1)==3 then sealIndex[g-905]=sent end
  target522,b522,p522=next522()
 end
end
"""


def run(a):
    evidence=json.loads((ROOT/"analysis/order520-verification.json").read_text())
    joint=json.loads((a.trace/"joint.json").read_text())
    selected=next(r["builds"]["candidate"] for r in evidence["phases"] if r["start_clock"]==joint["parameters"]["start"])
    for name,digest in selected["pins"].items():
        assert sha(a.trace/name)==digest
    assert sha(a.trace/"client.sfc")==sha(a.client/"sink165.sfc")==joint["client_SHA256"]
    a.out=a.out.resolve()
    a.out.mkdir(parents=True,exist_ok=False)
    a.frames=len(joint["frames"])
    assert a.frames==53
    shutil.copyfile(a.trace/"client.sfc",a.out/"client.sfc")
    for row in joint["frames"]:
        g=row["generation"]
        for name in (f"map-{g}.bin", f"expected-{g}.bin"):
            shutil.copyfile(a.trace/name,a.out/name)
    # Original RPC sequence numbers include ARM-only SYNCs. Only PUSH changes
    # the consumer queue. Compare every original consumer trace event below.
    with (a.out/"arrivals.tsv").open("w", newline="\n") as dst:
        last_clock=last_id=0
        for line in (a.trace/"packets.jsonl").read_text().splitlines():
            seq,at,b,tile=json.loads(line)
            assert seq>last_id and at>=last_clock
            dst.write(f"{at}\t{b}\t{tile}\n")
            last_id,last_clock=seq,at
        dst.write(f"{joint['frames'][-1]['ACK_masterclock']+1}\tFINISH\t\n")
    lua_rpc(a)
    lua=a.out/"capture.lua"
    s=lua.read_text()
    s=once(s,"   local hdma=file(",MAP_ORACLE+"   local hdma=file(")
    s=instrument(s,a)
    start=s.index("local sequence=0;")
    end=s.index("emu.addMemoryCallback(function()rpc()end",start)
    releases="\n".join(f"sourceRelease[{r['generation']}]={r['release_masterclock']}" for r in joint["frames"])
    s=s[:start]+releases+"\nlocal function unhex(b)return (b:gsub('..',function(c)return string.char(tonumber(c,16))end))end\n"+CLOCKED_INPUT+s[end:]
    a0=s.index("emu.addEventCallback(function()\n if sequence==1")
    a1=s.index("end,emu.eventType.endFrame)",a0)+len("end,emu.eventType.endFrame)")
    s=s[:a0]+s[a1:]
    # The receipt is confirmed at the token doorbell; the following bus ACK is
    # a distinct event. VRAM dest and command credit are captured before DMA.
    s=once(s,"  consumed[#consumed+1]=", '  sample516("receipt522",pw(16)+65536*pw(18));consumed[#consumed+1]=')
    s=once(s,'sample516("ppu_dma",dmaLength)', '''sample516("ppu_dma",dmaLength)
   sample516("dma_bbus522",regs[0x4301]);sample516("dma_source522",(regs[0x4304] or 0)*65536+(regs[0x4303] or 0)*256+(regs[0x4302] or 0))''')
    marker="local target522,b522,p522=next522()"
    labels=json.loads((a.client/"labels.json").read_text())
    obs=f"""emu.addMemoryCallback(function()
     sample516('credit522',word(0x1256));sample516('charge522',word(0x74));sample516('command522',word(0x1252))
    end,emu.callbackType.exec,{labels['wait169']})"""
    obs+=f"""\nemu.addMemoryCallback(function()
     sample516('issue_credit522',word(0x1256));sample516('issue_charge522',word(0x74))
     local i=word(0x1252);sample516('issue_index522',i)
     sample516('issue_src522',word(0x4000+i));sample516('issue_dst522',word(0x4002+i))
    end,emu.callbackType.exec,{labels['transfer212']})"""
    s=once(s,'sample516("ack",lastStatus)', '''sample516("ack",lastStatus)
   local listEnd=word(0x1250);sample516("list_end522",listEnd)
   if listEnd>=8 then
    sample516("tail_dst522",word(0x4000+listEnd-8+2))
    sample516("tail_len522",word(0x4000+listEnd-8+4))
   end''' )
    # An enqueued packet is visible to the CPU only when it polls $6000.
    # The retained callback runs rpc() before loaded() at each such read.
    s=once(s,"emu.addMemoryCallback(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)","")
    s=once(s,marker,obs+"\n"+marker)
    preamble="""local function checked522(callback)
 return function(...)
  local ok,result=pcall(callback,...)
  if not ok then
   local f=assert(io.open(ROOT..'/error.txt','a'))
   f:write(tostring(result),'\\n');f:close();emu.stop(1);return
  end
  return result
 end
end
local function addMem522(callback,...)return emu.addMemoryCallback(checked522(callback),...)end
local function addEvent522(callback,...)return emu.addEventCallback(checked522(callback),...)end
"""
    s=s.replace('emu.addMemoryCallback(', 'addMem522(').replace('emu.addEventCallback(', 'addEvent522(')
    s=once(s,'local function file(name)',preamble+'local function file(name)')
    lua.write_text(s,encoding="utf8",newline="\n")
    with (a.out/"mesen.log").open("wb") as log:
        subprocess.run([str(a.mesen.resolve()),"--testRunner",str(lua),str(a.out/"client.sfc"),"--timeout=1800",
                        "--doNotSaveSettings","--enableStdout","--snes.disableFrameSkipping=true",
                        "--debug.scriptWindow.allowIoOsAccess=true","--debug.scriptWindow.scriptTimeout=90"],
                       cwd=a.out,env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                       stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1850,creationflags=subprocess.CREATE_NO_WINDOW)
    result=json.loads((a.out/"result.json").read_text())
    assert result["passed"] and result["frames"]==joint["frames"] and result["commits"]==53
    with (a.out/"window.csv").open() as new,(a.trace/"window.csv").open() as old:
        assert [r for r in csv.DictReader(new) if not r["event"].endswith("522")]==list(csv.DictReader(old))
    for g in range(905,958):
        assert sha(a.out/f"frame-{g}.rgb")==sha(a.trace/f"frame-{g}.rgb")
    print("Verified 53 RGB frames, original 65816 trace and exact final ACK clocks.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("trace","client","mesen","out"):
        p.add_argument("--"+name,type=Path,required=True)
    run(p.parse_args())
