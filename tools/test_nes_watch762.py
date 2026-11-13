# SPDX-License-Identifier: MIT
"""Execute the packed receiver and materialize DMA writes for pin-level RTL replay."""
import runpy
import subprocess
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once

def instrument(script, fault=None):
    hook = """local wire762=assert(io.open(ROOT..'/wire762.csv','w'))
wire762:write('event,g,clock,source,port,byte\\n')
local ref762,off762,n762,lo762,ok762,err762={},0,0,nil,false,false
local function mark762(ev,src,p,v)
 wire762:write(string.format('%s,%d,%d,%d,%d,%d\\n',ev,word(0x1226),emu.getState().masterClock,src,p,v))
 wire762:flush()
end
checkedMem527(function(a,v)
 if a==0x6006 then lo762=v;ok762=false;return end
 assert(lo762 and not err762 and n762==0)
 off762=lo762+256*v;lo762=nil;n762=1536
 assert(regs[0x4304]==127 and off762==regs[0x4302]+256*regs[0x4303])
 assert(off762==word(0x1020)+0x5000+pending526.off and pending526.n==1536)
 mark762('arm',off762,0,0)
end,emu.callbackType.write,0x6006,0x6007)
checkedMem527(function()
 local v=ok762 and not err762 and 128 or 0
 mark762('read',off762,0,v);ok762=false
 return v
end,emu.callbackType.read,0x6006)
"""
    script=once(script,'local function write(a,v)',hook+'local function write(a,v)')
    script=once(script," if a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104 then", """ if n762>0 and (a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104) then
  local i=1536-n762
  local addr=off762+i
  local want=ref762[(addr-0x5000-word(0x1020))];assert(want~=nil)
  local seen=v
  FAULT762
  if a~=0x2118+(i%2) or seen~=want then err762=true end
  mark762('write',addr,a,seen)
  n762=n762-1;ok762=n762==0 and not err762
 end
 if a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104 then""".replace('FAULT762',{
        None:'', 'data':"if i==1535 and word(0x1226)==957 then seen=v~1 end",
        'stop':"if i==1534 and word(0x1226)==957 then err762=true end"}[fault]))
    script=once(script,'  lastStatus=ack[1];',"""  if ack[1]==0 and pb(0)==1 then ref762={} end
  if ack[1]==0 and pb(0)==2 and pb(1)==2 then
   for j=0,pw(12)-1 do ref762[pw(10)+j]=pb(16+j) end
  end
  lastStatus=ack[1];""")
    script=once(script,' if a==0x6001 then',' if a==0x6001 then\n  if err762 then return 128 end')
    return script


if __name__=='__main__':
    original=subprocess.Popen.__init__
    def launch(proc,argv,*args,**kwargs):
        if isinstance(argv,(list,tuple)) and '--testRunner' in argv:
            path=Path(argv[argv.index('--testRunner')+1])
            if path.name=='capture.lua':
                path.write_text(instrument(path.read_text(encoding='utf8')),encoding='utf8',newline='\n')
        original(proc,argv,*args,**kwargs)
    with patch.object(subprocess.Popen,'__init__',launch):
        runpy.run_module('test_nes_static751',run_name='__main__')
