# SPDX-License-Identifier: MIT
"""Reject forged row history, corrupt live edges and stale ACKs in the actual 515 client."""
import argparse
import json
from pathlib import Path
from test_nes_trim514_guards import LOADED, SETUP, main

# Give the cold spoof a matching serial and receipt bit so the unpublished-bank
# check, rather than an unrelated witness mismatch, must reject it.
COLD = """
  if MODE=='cold_partial' and op==10 then
   packet=packet:sub(1,14)..string.pack('<I2',word(0x1470))..packet:sub(17)
   for i=0,7 do
    emu.write(0x1460+i,255,emu.memType.snesWorkRam)
    emu.write(0x1480+i,0,emu.memType.snesWorkRam)
   end
  end
"""
FAULTS = """
   if op==10 then
    if MODE=='legacy_opcode' then packet=string.char(10)..packet:sub(2) end
    local at,len=pw(10),pw(12)
    local omitted=at%64>0 and at//64*64 or at+len
    local row=omitted//64;local bit=1<<(row%8)
    local ix=bank*8+row//8
    if MODE=='missing_receipt' then
     emu.write(0x1460+ix,rd(0x1460+ix)&(~bit),emu.memType.snesWorkRam)
     emu.write(0x1480+ix,rd(0x1480+ix)|bit,emu.memType.snesWorkRam)
    elseif MODE=='corrupt_receipt' then
     emu.write(0x1480+ix,rd(0x1480+ix)~bit,emu.memType.snesWorkRam)
    elseif MODE=='corrupt_serial' then
     emu.write(0x1470+bank*2,rd(0x1470+bank*2)~1,emu.memType.snesWorkRam)
    elseif MODE=='last_edge_byte' then
     local stop=at%64>0 and at or ((at+len+63)//64)*64
     local address=0x15000+bank*0x8000+stop-1
     emu.write(address,rd(address)~128,emu.memType.snesWorkRam)
    end
   end
"""
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','out','mesen'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'))
    p.add_argument('--stop-only',action='store_true',help='Replay the two STOP injections for the instruction timing sample')
    a=p.parse_args();a.out=a.out.resolve();a.client=a.client.resolve()
    begin=LOADED.index("  if MODE=='cold_partial'")
    end=LOADED.index("  if MODE=='cold_missing'",begin)
    loaded=(LOADED[:begin]+COLD+LOADED[end:]).replace("   visibleBefore=",FAULTS+"   visibleBefore=")
    setup=SETUP.replace("local function save_maps()", """local function save_maps()
 local f=assert(io.open(ROOT..'/history.bin','wb'))
 for i=0x1460,0x148f do f:write(string.char(rd(i)))end
 f:close()""").replace("if MODE=='normal' then", """if MODE=='normal' then
 local previous=file('../stop_final/history.bin')
 for i=0,#previous-1 do emu.write(0x1460+i,previous:byte(i+1),emu.memType.snesWorkRam)end""")
    labels=json.loads((a.client/'labels.json').read_text())
    setup+="""
local stopRead515=nil
local function stamp_stop515()
 stopRead515=stopRead515 or emu.getState().masterClock
 return 128
end
if MODE=='stop_check' or MODE=='stop_final' then
 local first,invalid
 local function clock()return emu.getState().masterClock end
 emu.addMemoryCallback(function()first=clock()end,emu.callbackType.exec,@FAIL@)
 emu.addMemoryCallback(function()
  invalid=clock();assert(word(0x1260)==0,'both banks still authorized')
 end,emu.callbackType.exec,@NEXT@)
 emu.addMemoryCallback(function()
  if stopRead515 and invalid then
   local f=assert(io.open(ROOT..'/stop-clocks.txt','w'))
   f:write(invalid-first,' ',clock()-stopRead515);f:close()
  end
 end,emu.callbackType.write,0x601c)
end
""".replace('@STOP@',str(labels['stop_packet'])).replace('@FAIL@',str(labels['fail'])).replace('@NEXT@',str(labels['fail']+3))
    main(a,setup=setup,stop_response='stamp_stop515()',modes=('stop_check','stop_final') if a.stop_only else None,extra_modes=('legacy_opcode','missing_receipt','corrupt_receipt','corrupt_serial','last_edge_byte'),
         loaded=loaded.replace("op==10","op==11"),bad_witness='bad_serial',opcode=11)
