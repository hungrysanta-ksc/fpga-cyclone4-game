"""723 linked ARM with725 native65816; extend only the DMA ownership oracle.

Accepted-range/bytes, inactive bank, fresh beam, retire and final pixels retain
the original independent oracle. An owned head is still unacknowledged.
"""
import json,runpy
from pathlib import Path
from unittest.mock import patch
import test_nes_progress680 as progress
from nes_raw506 import once

def owned(s,a):
    labels=json.loads((a.client/'labels.json').read_text())
    s=once(s,' assert(not packet and not pending526 and bank~=word(0x1032) and word(0x1228)==1 and i<=tail)',
        ''' local owned=packet and pb(0)==7 and word(0x1228)==3
 assert(((not packet and word(0x1228)==1) or owned) and not pending526 and bank~=word(0x1032) and i<=tail)
 if owned then
  assert(pb(1)<2 and pw(8)==word(0x1226) and pw(2)==word(0x1220))
  assert(pw(4)==word(0x1222) and pw(6)==word(0x1224))
  assert(pw(14)>0 and pw(14)<=2048 and pw(10)%(pb(1)==0 and 16 or 32)==0)
 end''')
    s+='''
local log725=assert(io.open(ROOT..'/owner725.csv','w'))
log725:write('generation,event,clock,state,op,section,sequence\\n');log725:flush()
local function owner725(name)
 assert(packet and pb(0)==7 and word(0x1228)==1,'bulk ownership boundary')
 log725:write(string.format('%d,%s,%d,%d,%d,%d,%d\\n',word(0x1226),name,emu.getState().masterClock,word(0x1228),pb(0),pb(1),pw(2)));log725:flush()
end
'''
    s+=f"checkedMem527(function()owner725('enter')end,emu.callbackType.exec,{labels['owned_bulk725']})\n"
    s+=f"checkedMem527(function()if packet and pb(0)==7 then owner725('leave')end end,emu.callbackType.exec,{labels.get('owned_return725',labels['data'])})\n"
    s+=f"checkedMem527(function()assert(word(0x1228)~=3,'transient owner leaked to ACK')end,emu.callbackType.exec,{labels['reply']})\n"
    return s

original=runpy.run_module

def execute(name,*args,**kwargs):
    if name!='test_nes_complete685':return original(name,*args,**kwargs)
    path=Path(__file__).with_name(name+'.py');s=path.read_text()
    s=once(s,'    return s\n', '    return extend725(s,a)\n')
    exec(compile(s,str(path),'exec'),dict(__name__='__main__',__file__=str(path),extend725=owned))

if __name__=='__main__':
    with patch.object(runpy,'run_module',execute):
        runpy.run_module('test_nes_observer717',run_name='__main__')
