# SPDX-License-Identifier: MIT
"""STOP with a pending map span and at packet-final flush; actual65816."""
import inspect
import test_nes_maskfault247 as base
from nes_delta231 import once

CASES=('stop_batch_pending','stop_batch_final')


def main():
 s=inspect.getsource(base.main)
 s=once(s,"  lua=once(lua,' if a==0x6001 then',", '''  labels=json.loads((a.client/'labels.json').read_text())
  hooks="local batchStop247=false\\n"
  for label in ('batch_ranged247','batch_flush247'):
   hooks+='emu.addMemoryCallback(function() if packet and pw(8)==2 then if (MODE=="stop_batch_pending" and '+str(label=='batch_ranged247').lower()+' and word(0x148e)>=2) or (MODE=="stop_batch_final" and '+str(label=='batch_flush247').lower()+' and word(0x80)==pw(12)) then batchStop247=true end end end,emu.callbackType.exec,'+str(labels[label])+')\\n'
  at=lua.index('emu.addMemoryCallback(');lua=lua[:at]+hooks+lua[at:]
  lua=once(lua,' if a==0x6001 then',' if a==0x6001 then if batchStop247 then return 128 end')
  lua=once(lua,' if a==0x6001 then', ''')
 ns=dict(base.__dict__);ns.update(CASES=CASES,__file__=__file__,__doc__=__doc__);exec(compile(s,'batchstop247','exec'),ns);ns['main']()


if __name__=='__main__':main()
