# SPDX-License-Identifier: MIT
"""Clock-preserving 727 replay with a WRAM watch from final ACK to target reuse."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch
import replay_nes_map527 as replay
from nes_raw506 import once

WATCH = """
local tracked=false
local target,ptr=0,0
local out738=assert(io.open(ROOT..'/writes738.csv','w'))
out738:write('event,g,clock,address,count,value\\n')
local function log738(event,address,n,value)
 out738:write(string.format('%s,%d,%d,%d,%d,%d\\n',event,packet and pw(8) or -1,emu.getState().masterClock,address,n,value or 0))
end
local function snap738(key)
 local a={}
 for i=0,1753 do a[i+1]=string.char(rd(target+i)) end
 local f=assert(io.open(ROOT..'/'..key..'.bin','wb'));f:write(table.concat(a));f:close()
 log738(key,target,1754,0);out738:flush()
end
checkedMem527(function(a,v)
 if tracked and a>=0x7e0000+target and a<0x7e0000+target+1754 then log738('direct',a-0x7e0000,1,v) end
end,emu.callbackType.write,0x7f0000,0x7fffff)
checkedMem527(function(a,v)
 if a==0x2181 then ptr=(ptr&0x1ff00)|v
 elseif a==0x2182 then ptr=(ptr&0x100ff)|(v<<8)
 elseif a==0x2183 then ptr=(ptr&65535)|((v&1)<<16)
 else
  if tracked and ptr>=target and ptr<target+1754 then log738('port',ptr,1,v) end
  ptr=(ptr+1)&0x1ffff
 end
end,emu.callbackType.write,0x2180,0x2183)
checkedMem527(function()
 if tracked and regs[0x4301]==0x80 then
  local n=(regs[0x4305] or 0)+256*(regs[0x4306] or 0)
  log738('DMA_to_WRAM',ptr,n,0)
 end
end,emu.callbackType.write,0x420b)
"""


def observe(_,a,unused):
    for f in a.trace.glob('colors636-*.bin'):
        shutil.copyfile(f,a.out/f.name)
    s=(a.trace/'capture.lua').read_text(encoding='utf8')
    s=once(s,'local ROOT='+json.dumps(a.trace.resolve().as_posix()),'local ROOT='+json.dumps(a.out.as_posix()))
    s=once(s,'checkedMem527(function()rpc()end','emu.addMemoryCallback(function()rpc()end')
    s=once(s,'checkedEvent527(function()\n if sequence==1','emu.addEventCallback(function()\n if sequence==1')
    s=once(s,'local trace516=',WATCH+'\nlocal trace516=')
    s=once(s,' if pb(0)==7 then tile=tilePayload',""" if pw(8)==957 and pb(0)==1 then snap738('begin957') end
 if pw(8)==957 and pb(1)==5 and pw(10)==0 then
  assert(0x16500+word(0x1020)==target)
  snap738('before957')
 end
 if pb(0)==7 then tile=tilePayload""")
    return once(s,'  lastStatus=ack[1];',"""  if pb(0)==3 and ack[1]==1 then
   if pw(8)==955 then target=0x16500+word(0x1020);tracked=true;snap738('ack955')
   elseif pw(8)==956 then assert(target~=0x16500+word(0x1020));snap738('ack956')
   elseif pw(8)==957 then snap738('ack957');tracked=false end
  end
  lastStatus=ack[1];""")


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','out','mesen','client'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.frames=53
    with patch.object(replay,'observe',observe):
        replay.run(a)
