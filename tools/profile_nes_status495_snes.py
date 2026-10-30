# SPDX-License-Identifier: MIT
"""Read-only actual489 SNES interval profile, with unchanged pixels/ACK guards.

Inclusive intervals may nest; service/DMA/VBlank waits are retained.
File-aperture/4credit/2.625Mbps model is not common physical ARM/IRQ/ROM time.
"""
import json,sys
from pathlib import Path
from nes_status495 import ROOT
if __name__=='__main__':
    client=Path(sys.argv[sys.argv.index('--client')+1]);labels=json.loads((client/'labels.json').read_text());body=(client/'body.bin').read_bytes()
    events={}
    for name in ['local165_entry','validate181','coverage212','append212','upload165_entry','raw_dma489','service']:
        pc=labels[name];needle=bytes([0x20,pc&255,(pc>>8)&255]);hits=[i for i in range(len(body)-2)if body[i:i+3]==needle]
        assert hits,name;events[name]={'entry':pc,'returns':[0x7e2000+i+3 for i in hits]}
    events['compact_rows489']={'entry':labels['compact_rows489'],'returns':[labels['compact_ok489']]}
    extra=r'''
if COMPACT then
 local pf=assert(io.open(ROOT..'/profile495.csv','w'));pf:write('generation,ordinal,name,inclusive_master_clocks\n')
 local stack={}
 local function enter(name)
  if not packet then return end
  assert(not stack[name],'recursive profile interval');stack[name]={clock=emu.getState().masterClock,gen=pw(8),idx=index}
 end
 local function leave(name)
  local p=stack[name];if not p then return end;stack[name]=nil
  pf:write(string.format('%d,%d,%s,%d\n',p.gen,p.idx,name,emu.getState().masterClock-p.clock));pf:flush()
 end
@HOOKS@
end
'''
    hooks=[]
    for name,e in events.items():
        hooks.append(' emu.addMemoryCallback(function()enter('+json.dumps(name)+')end,emu.callbackType.exec,'+str(e['entry'])+')')
        for at in e['returns']:hooks.append(' emu.addMemoryCallback(function()leave('+json.dumps(name)+')end,emu.callbackType.exec,'+str(at)+')')
    extra=extra.replace('@HOOKS@','\n'.join(hooks))
    s=(ROOT/'tools/test_nes_output489_snes.py').read_text();needle="if __name__=='__main__':";assert s.count(needle)==1
    s=s.replace(needle,'LUA += '+repr(extra)+'\n'+needle)
    exec(compile(s,str(ROOT/'tools/test_nes_output489_snes.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_output489_snes.py')})
