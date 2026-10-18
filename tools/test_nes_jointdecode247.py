# SPDX-License-Identifier: MIT
"""Actual C2472 sender ->65816, independent complete receipt and map oracle."""
from pathlib import Path
import inspect,json,sys
import test_nes_maskrun247 as base
from nes_delta231 import once

CHECK=r'''
  if ack[1]==0 and pb(0)==1 then receipt247={};for i=0,255 do receipt247[i]=0 end end
  if ack[1]==0 and pb(0)==9 then
   local at=17;assert(pb(16)==3)
   while at<#packet do
    local offset=pw(at);local n=pb(at+2)*2;at=at+3
    for i=0,n-1 do assert(rd(0x15000+word(0x1020)+offset+i)==pb(at+i),'span staging mismatch')end
    for w=offset//2,(offset+n)//2-1 do
     local index=w//8;local bit=1<<(w%8);assert((receipt247[index]&bit)==0,'sender duplicate')
     receipt247[index]=receipt247[index]|bit
    end
    at=at+n
   end
   assert(at==#packet)
   for i=0,255 do assert(rd(0x1500+i)==receipt247[i],'complete receipt mismatch')end
  end
  if ack[1]==0 and pb(0)==10 then
   for i=0,pw(12)-1 do assert(pb(16+i)==receipt247[pw(10)+i],'dense manifest mismatch')end
   assert(word(0x1490)==pw(10)+pw(12),'manifest cursor mismatch')
  end
  if ack[1]==0 and pb(0)==11 then
   local at=17;local offset=pw(10);assert(pb(16)==3)
   while at<#packet do
    local code=pb(at);at=at+1;local n=(code&127)+1
    for i=0,n-1 do local value=0;if code<128 then value=pb(at);at=at+1 end
     assert(receipt247[offset]==value,'RLE manifest mismatch');offset=offset+1
    end
   end
   assert(at==#packet and word(0x1490)==offset,'RLE manifest cursor')
  end
  if ack[1]==1 then assert(rd(0x148c+word(0x1034))==1,'missing map initialization')end
'''


def main():
 client=Path(sys.argv[sys.argv.index('--client')+1]);labels=json.loads((client/'labels.json').read_text())
 extra="\nlocal receipt247={}\nlocal joint247=assert(io.open(OUT_DIR..'/joint-detail247.csv','w'))\njoint247:write('generation,ordinal,event,clock\\n')\n"
 for name in ('span_record247','span_service247','span_serviced247','manifest_run247','manifest_service247','manifest_serviced247'):
  extra+='emu.addMemoryCallback(function()joint247:write(string.format("%d,%d,'+name+',%d\\n",pw(8),ordinal,emu.getState().masterClock));joint247:flush()end,emu.callbackType.exec,'+str(labels[name])+')\n'
 # Lua callback errors can be logged while the emulator continues. Fail the
 # runner before it writes a successful result if any assertion was logged.
 s=inspect.getsource(base.baseline.main)
 s=once(s,"        result=json.loads", "        assert not (run/'lua-error.txt').exists() or not (run/'lua-error.txt').read_text().strip(),'Lua callback assertion recorded'\n        result=json.loads")
 ns=dict(base.baseline.__dict__);exec(compile(s,'jointdecode247-strict-runner','exec'),ns)
 original=base.inspect.getsource
 def getsource(fn):return s if fn is ns['main'] else original(fn)
 base.baseline.main=ns['main'];base.inspect.getsource=getsource
 base.OBSERVE+=extra;base.CHECK=CHECK;base.__file__=__file__;base.__doc__=__doc__;base.main()


if __name__=='__main__':main()
