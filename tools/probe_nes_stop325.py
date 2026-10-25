# SPDX-License-Identifier: MIT
"""Execute native STOP acknowledgement and invalidate previously reused zero bank."""
import inspect
import probe_nes_consumer325 as native
from nes_delta231 import once

def main():
 s=inspect.getsource(native.main)
 s=once(s,' if a==0x6000 then return event(0,a,1)end',' if a==0x6000 then if at>#cases then return 0 end;return event(0,a,1)end')
 s=once(s,' if a==0x6001 then return event(0,a,0)end',' if a==0x6001 then if at>#cases then return 0 end;return event(0,a,(at==2 and not stopped325) and 64 or 0)end')
 s=once(s,'local descriptor_reads=0','''local descriptor_reads=0
local stopped325=false
emu.addMemoryCallback(function(a,v)
 assert(at==2 and not stopped325 and v==0xa5,'native STOP acknowledgement '..tostring(at)..'/'..tostring(stopped325)..'/'..tostring(v))
 stopped325=true;event(1,a,v)
end,emu.callbackType.write,0x6006)''')
 s=once(s,' ns=dict(base.__dict__);',''' def expected(cases,mode):
  fills,decisions=base.expected_fills(cases,mode)
  return fills+1,decisions
 ns=dict(base.__dict__);ns['expected_fills']=expected;''')
 ns=dict(native.__dict__);exec(compile(s,'native-stop325','exec'),ns);ns['main']()

if __name__=='__main__':main()
