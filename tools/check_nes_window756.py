# SPDX-License-Identifier: MIT
"""Fault a real 957 map delta before, and inside, its 65816 restore loop."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from nes_raw506 import once,sha
from check_nes_group628 import SAVE_MAPS


def run(a):
    original=replay.run
    a.mode='stop' if a.fault=='partial' else 'stale'
    def checked(args,*,edit_script):
        def edit(s):
            s=edit_script(s)
            if a.fault=='partial':
                s=once(s,"  if rejected or quiet739 then\n   local screen=", "  if rejected or quiet739 then"+SAVE_MAPS+"\n   local screen=")
                s=once(s,'if pw(8)==957 and pb(0)==9 then stop739=true end','')
                pc=json.loads((a.client/'labels.json').read_text())['row628']
                return once(s,'local function loaded()',f"""local seen756=0
checkedMem527(function()
 if packet and pw(8)==957 and pb(0)==9 and pb(1)==2 and pw(10)==2048 and not stop739 and seen756==1 then
  stop739=true
  local f=assert(io.open(ROOT..'/partial756.txt','w'));f:write(index);f:close()
 end
 if packet and pw(8)==957 and pb(0)==9 and pb(1)==2 and pw(10)==2048 then seen756=seen756+1 end
end,emu.callbackType.exec,{pc})
local function loaded()""")
            actions={
              'identity':'packet=packet:sub(1,16)..string.char(pb(16)~1)..packet:sub(18)',
              'checksum':'packet=packet:sub(1,20)..string.char(pb(20)~1)..packet:sub(22)',
              'retained':"""local unchanged=nil
 for i=0,47 do if pb(24+i//8)&(1<<(i%8))==0 then unchanged=i;break end end
 assert(unchanged~=nil)
 local address=0x10000+word(0x1020)+0x5000+pw(10)+4*unchanged
 emu.write(address,rd(address)~1,emu.memType.snesWorkRam)"""}
            return once(s,"if pw(8)==957 and pb(0)==9 then\n  packet=packet:sub(1,128)..string.char(pb(128)~1)..packet:sub(130)",
                        "if pw(8)==957 and pb(0)==9 and pb(1)==2 and pw(10)==2048 then\n  "+actions[a.fault])
        return original(args,edit_script=edit)
    with patch.object(replay,'run',checked):
        owner.run(a)
    r=json.loads((a.out/'result.json').read_text())
    assert r['commits']==52 and r['last_status']==(228 if a.fault=='partial' else 224)
    if a.fault=='partial':
        assert (a.out/'partial756.txt').stat().st_size>0
        recover(a)
    return dict(fault=a.fault,commits=r['commits'],status=r['last_status'],retained=sha(a.out/'retained.rgb'))

def recover(a):
    import shutil
    from copy import copy
    cold=copy(a)
    cold.out=a.out/'restart'
    cold.frames=2
    def inject(s):
        shutil.copyfile(a.out/'stopped-maps.bin',cold.out/'stopped-maps.bin')
        assert (cold.out/'stopped-maps.bin').stat().st_size==16384
        s=once(s,"MODE=='normal'and 53", "MODE=='normal'and 2")
        return once(s,'local function loaded()',"""local old=file('stopped-maps.bin')
local j=1
for bank=0,1 do for _,vram in ipairs({false,true}) do
 local at=vram and (0x6000+bank*0x4000) or (0x15000+bank*0x8000)
 for i=0,4095 do emu.write(at+i,old:byte(j),vram and emu.memType.snesVideoRam or emu.memType.snesWorkRam);j=j+1 end
end end
for i=0,7 do emu.write(0x14d0+i,0xa5,emu.memType.snesWorkRam)end
local coldChecked=false
local function loaded()
 if not coldChecked then for i=0,6,2 do assert(word(0x14d0+i)==0,'cold identity')end;coldChecked=true end""")
    with patch.object(replay,'observe',owner.observe):
        replay.run(cold,edit_script=inject)
    assert json.loads((cold.out/'result.json').read_text())['last_status']==1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','out','mesen','client'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--fault',choices=('partial','identity','checksum','retained'),required=True)
    a=p.parse_args()
    r=run(a)
    (a.out/'verified756.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
