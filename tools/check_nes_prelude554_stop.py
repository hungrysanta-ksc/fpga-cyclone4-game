# SPDX-License-Identifier: MIT
"""Cancel generation 954 after its first staged palette, OAM or HDMA packet."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_seal538_stop import exercise


def cancel(lua,labels,section):
    # Inject when the next ordinary head is already owned. A STOP while the
    # consumer is idle need not return an error ACK for any packet.
    lua=once(lua,'local function loaded()',f"""local seen554,armed554,sampled554=false,false,false
emu.addMemoryCallback(function()
 if packet and pw(8)==FAULT and pb(1)=={section} and pw(10)==0 then seen554=true end
end,emu.callbackType.exec,{labels['accepted']})
emu.addMemoryCallback(function()
 if seen554 and packet and pw(8)==FAULT and pb(1)=={section} and pw(10)>0 then armed554=true end
end,emu.callbackType.exec,{labels['header']})
local function loaded()""")
    lua=once(lua,'if a==0x6001 then','if a==0x6001 then if armed554 then sampled554=true;return 128 end')
    lua=once(lua,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
    lua=once(lua,'if a>=0x4300 and a<=0x4306 then',
             "if sampled554 and a==0x420b then error('DMA after sampled STOP') end\n if a>=0x4300 and a<=0x4306 then")
    lua=once(lua,"assert(lastStatus==0xe4,'STOP status')","assert(sampled554 and lastStatus==0xe4 and word(0x125a)==0,'STOP state')")
    lua=lua.replace('emu.addMemoryCallback(','mem554(').replace('emu.addEventCallback(','event554(')
    return once(lua,'local function file(name)',"""local function trap554(f)
 return function(...)
  local ok,val=pcall(f,...)
  if ok then return val end
  local err=assert(io.open(ROOT..'/failure.txt','w'));err:write(tostring(val));err:close();emu.stop(1)
 end
end
local function mem554(f,...)return emu.addMemoryCallback(trap554(f),...)end
local function event554(f,...)return emu.addEventCallback(trap554(f),...)end
local function file(name)""")


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('client','trace','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((a.client/'labels.json').read_text())
    rows=[exercise(a,954,f'staged-{k}',edit_packet_case=lambda s:cancel(s,labels,k)) for k in (3,4,5)]
    (a.out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
