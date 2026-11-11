"""Interrupt the merged section-5 transfer across the old 1121-byte boundary."""
import argparse
import json
import tempfile
from pathlib import Path

from nes_raw506 import once
from test_nes_seal538_stop import exercise


def inject(source, stop_at):
    # Report the first fixture error instead of a later emulator timeout.
    source = once(source, 'local function file(name)', """local function checked(fn)
 return function(...)
  local ok,value=pcall(fn,...)
  if not ok then
   local log=assert(io.open(ROOT..'/first-error.txt','w'));log:write(tostring(value));log:close();emu.stop(1)
  end
  return value
 end
end
local mem,evt=emu.addMemoryCallback,emu.addEventCallback
emu.addMemoryCallback=function(fn,...) return mem(checked(fn),...) end
emu.addEventCallback=function(fn,...) return evt(checked(fn),...) end
local function file(name)""")
    source = once(source, 'local function loaded()', """
local restored,armed,stopped,base,endoffset=0,false,false,nil,nil
local function joined()
 return packet and pw(8)==FAULT and pb(0)==5 and pb(1)==5 and pw(10)<1121 and pw(10)+pw(14)>1121
end
emu.addMemoryCallback(function()
 if joined() then
  assert(not stopped,'DMA after STOP')
  local n=regs[0x4305]+256*regs[0x4306]
  assert(n==math.min(64,endoffset-restored),'bounded fill')
  restored=restored+n
  if restored==STOP_AT then armed=true end
 end
end,emu.callbackType.write,0x420b)
local function loaded()""".replace('STOP_AT', str(stop_at)))
    source = once(source, ' if pb(0)==7 then tile=file', """
 if joined() then
  base=0x16500+word(0x1020)+pw(10)
  endoffset=pw(14)
  for i=0,endoffset-1 do emu.write(base+i,0x5a,emu.memType.snesWorkRam) end
 end
 if pb(0)==7 then tile=file""")
    source = once(source, "if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
    source = once(source,'if a==0x6001 then','if a==0x6001 then if armed then stopped=true;return 128 end')
    return once(source,"assert(lastStatus==0xe4,'STOP status')",
                """assert(lastStatus==0xe4 and stopped and restored==STOP_AT,'STOP status')
 for i=0,endoffset-1 do assert(rd(base+i)==(i<restored and 0 or 0x5a),'partial fill') end""".replace('STOP_AT',str(stop_at)))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('trace','client','mesen','out'):
        p.add_argument(name,type=Path)
    p.add_argument('--generation',type=int,default=906)
    a=p.parse_args()
    a.out=a.out.resolve()
    a.out.mkdir(exist_ok=False)
    destination=a.out
    if not str(destination).isascii():
        # The shared fixture expands its root as a Lua string via JSON.
        # Keep a uniquely named ASCII fixture for the runner and its raw logs.
        a.out=Path(tempfile.mkdtemp(prefix='nes-tail735-stop-',dir=a.trace.resolve().parent))
    results=[exercise(a,a.generation,f'chunk{n}',edit_packet_case=lambda s:inject(s,n)) for n in (64,1152)]
    (destination/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    (destination/'fixture-path.txt').write_text(str(a.out)+'\n')
