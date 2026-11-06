# SPDX-License-Identifier: MIT
"""Execute padding-hit, cold, corruption, partial STOP and two-bank restart in Mesen."""
import argparse
import json
import shutil
from pathlib import Path
from check_nes_group628 import SAVE_MAPS, recover
from check_nes_tail631 import SAVE_REGIONS
from nes_raw506 import once
from test_nes_seal538_stop import exercise

PAD = "pb(0)==5 and pb(1)==5 and pw(16)==0 and pw(10)+pw(14)==1121"


def inject(source, labels, case):
    prefix = f"""
local chunks,restored,hits=0,0,0
local armed,prepared=false,false
local function pad() return packet and pw(8)==FAULT and {PAD} end
local function poison()
 local start=0x16500+word(0x1020)+pw(10)
 for i=0,pw(14)-1 do emu.write(start+i,0x5a,emu.memType.snesWorkRam) end
end
emu.addMemoryCallback(function()
 if pad() then hits=hits+1;armed=true end
end,emu.callbackType.exec,{labels['hit647']})
emu.addMemoryCallback(function()
 if pad() then
  assert(not armed,'DMA after STOP')
  local n=regs[0x4305]+256*regs[0x4306]
  assert(n==math.min(64,1100-restored),'chunk')
  chunks=chunks+1;restored=restored+n
  if '{case}'=='stop' and restored==64 then armed=true end
 end
end,emu.callbackType.write,0x420b)
local function loaded()"""
    source=once(source,"local function loaded()",prefix)
    preparation = "prepared=true;"
    if case in ("stop","corrupt"):
        preparation += """local addr=0x14e2+4*word(0x1034)
 assert(word(addr-2)==22 and word(addr)==65513,'prior receipt')
 emu.write(addr,rd(addr)~1,emu.memType.snesWorkRam);poison()"""
    if case=="cold":
        preparation += "assert(word(0x14e0+4*word(0x1034))==0);poison()"
    source=once(source," if pb(0)==7 then tile=file",
                f" if pad() and not prepared then {preparation} end\n if pb(0)==7 then tile=file")
    source=once(source,"if a==0x6001 then","if a==0x6001 then if armed then return 128 end")
    source=once(source,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",
                "if MODE=='stop_final' and rd(0x1025)==2 then return 128 end")
    if case in ("corrupt","cold"):
        source=once(source,"  lastStatus=ack[1]", """  if pad() then
   assert(ack[1]==0 and chunks==18 and restored==1100 and hits==0,'incomplete repair')
   for i=0,1099 do assert(rd(0x16500+word(0x1020)+pw(10)+i)==0,'repair data') end
  end
  lastStatus=ack[1]""")
    expected={"stop":(1,64,0),"hit":(0,0,1),"corrupt":(18,1100,0),"cold":(18,1100,0)}[case]
    checks=f"""assert(prepared and chunks=={expected[0]} and restored=={expected[1]} and hits=={expected[2]})
 for i=0,8,2 do assert(word(0x14e0+i)==0,'uncleared padding history') end"""
    if case=="stop":
        checks+="""
 local base=0x16500+word(0x1020)+21
 for i=0,1099 do assert(rd(base+i)==(i<64 and 0 or 0x5a),'partial WRAM')end"""+SAVE_MAPS+SAVE_REGIONS
    return once(source,"assert(lastStatus==0xe4,'STOP status')","assert(lastStatus==0xe4,'STOP status');"+checks)


def restart(out,source):
    shutil.copyfile(out.parent/'907-stop/stopped-tail.bin',out/'tail.bin')
    source=once(source,"local function loaded()",f"""local old=file('tail.bin');local j=1
for bank=0,1 do for i=0x6200,0x6960 do
 emu.write(0x10000+bank*0x8000+i,old:byte(j),emu.memType.snesWorkRam);j=j+1
end end
for i=0,9 do emu.write(0x14e0+i,0xa5,emu.memType.snesWorkRam)end
local full=0
emu.addMemoryCallback(function()
 if packet and {PAD} then full=full+1 end
end,emu.callbackType.write,0x420b)
local function loaded()""")
    source=once(source,"packet=requests[index];","if index==1 then for i=0,8,2 do assert(word(0x14e0+i)==0)end end;packet=requests[index];")
    return once(source,"assert(captured==commits)","assert(full==36,'two full cold restores');assert(captured==commits)")


def main(a):
    a.out=a.out.resolve()
    a.out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((a.client/"labels.json").read_text())
    a.generation=907
    cases=[exercise(a,gen,case,edit_packet_case=lambda s:inject(s,labels,case))
           for gen,case in ((906,"cold"),(907,"stop"),(907,"hit"),(908,"hit"),(907,"corrupt"))]
    result=dict(cases=cases,restart=recover(a,prepare_script=restart))
    (a.out/"guards.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("trace","client","mesen","out"):
        p.add_argument("--"+name,type=Path,required=True)
    main(p.parse_args())
