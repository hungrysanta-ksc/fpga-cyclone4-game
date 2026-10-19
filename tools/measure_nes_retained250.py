# SPDX-License-Identifier: MIT
"""Observe retained command/layout work in the unchanged2472 SNES receiver.

No check is bypassed and no product binary is changed. Removing a measured
bitmap interval in analysis is a counterfactual, not a new consumer timing.
"""
from pathlib import Path
import json,sys
import test_nes_jointdecode247 as joint

OBSERVE=r'''
local retained250=assert(io.open(OUT_DIR..'/retained250.csv','w'))
retained250:write('generation,ordinal,op,section,event,clock\n')
local function retainedhook250(name)
 retained250:write(string.format('%d,%d,%d,%d,%s,%d\n',pw(8),ordinal,pb(0),pb(1),name,emu.getState().masterClock));retained250:flush()
end
'''

def main():
 client=Path(sys.argv[sys.argv.index('--client')+1]);labels=json.loads((client/'labels.json').read_text())
 body=(client/'body.bin').read_bytes();base=0x7e2000;hooks={}
 for name in ('mark212','validate181','coverage212','append212'):
  hooks[name]=labels[name];target=labels[name]&65535;needle=bytes((0x20,target&255,target>>8))
  hits=[i for i in range(len(body)-2) if body[i:i+3]==needle];assert hits,(name,hits)
  if name!='append212':assert len(hits)==1,(name,hits)
  for i,at in enumerate(hits):hooks[name+'_return'+str(i)]=base+at+3
 # The first post-bitmap instruction loads section60, then skips CGRAM.
 needle=bytes.fromhex('a6 60 e0 06 00');hits=[i for i in range(len(body)-len(needle)+1) if body[i:i+len(needle)]==needle]
 assert len(hits)==1,hits
 hooks['address250']=base+hits[0];hooks['bits212']=labels['bits212']
 extra=OBSERVE
 for name,pc in hooks.items():extra+='emu.addMemoryCallback(function()retainedhook250('+json.dumps(name)+')end,emu.callbackType.exec,'+str(pc)+')\n'
 joint.base.OBSERVE+=extra;joint.__file__=__file__;joint.__doc__=__doc__;joint.main()

if __name__=='__main__':main()
