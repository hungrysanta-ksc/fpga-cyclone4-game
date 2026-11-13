# SPDX-License-Identifier: MIT
"""Measure staging token writes and the checked OAM completion on immutable 727-family offers."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from nes_raw506 import once, sha


def observe(_, a, unused):
    for path in a.trace.glob('colors636-*.bin'):
        shutil.copyfile(path, a.out/path.name)
    s=(a.trace/'capture.lua').read_text(encoding='utf8')
    s=once(s,'local ROOT='+json.dumps(a.trace.resolve().as_posix()),'local ROOT='+json.dumps(a.out.as_posix()))
    s=once(s,'checkedMem527(function()rpc()end','emu.addMemoryCallback(function()rpc()end')
    s=once(s,'checkedEvent527(function()\n if sequence==1','emu.addEventCallback(function()\n if sequence==1')
    return s


def run(a):
    a.frames=53
    negative=a.mode!='trace'
    def edit(s):
        labels=json.loads((a.client/'labels.json').read_text())
        s=once(s,'local trace516=', """local audit739=assert(io.open(ROOT..'/owner.csv','w'))
audit739:write('event,g,index,clock,frame,line,kind,value\\n')
local function owner739(event,value)
 if packet and pw(8)==957 then
  local st=emu.getState()
  audit739:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d\\n',event,pw(8),index,st.masterClock,
   st.frameCount,st['ppu.scanline'],pb(1),value));audit739:flush()
 end
end
local active739,logged739=false,{}
checkedMem527(function()
 if active739 then
  local st=emu.getState();local line=st['ppu.scanline']
  if line>=225 and line<=260 and not logged739[st.frameCount] then
   audit739:write(string.format('beam,957,%d,%d,%d,%d,0,%d\\n',index,st.masterClock,st.frameCount,line,st['memoryManager.hClock']))
   logged739[st.frameCount]=true;audit739:flush()
  end
 end
end,emu.callbackType.read,0x4212)
local trace516=""")
        s=once(s,' if pb(0)==7 then tile=tilePayload',' if pw(8)==957 then active739=true end\n if pb(0)==7 then tile=tilePayload')
        s=once(s,'  consumed[#consumed+1]',"  owner739('bank_release',pw(16)+65536*pw(18))\n  consumed[#consumed+1]")
        for point in ('reuse635','proven635','data'):
            handler=f"checkedMem527(function() if packet and pb(0)==9 then owner739('{point}',word(0x14da)) end end,emu.callbackType.exec,{labels[point]})\n"
            s=once(s,'local function loaded()',handler+'local function loaded()')
        if negative:
            s=once(s,"local MODE='normal'",f"local MODE='{a.mode}'")
            s=once(s,'local FAULT=905','local FAULT=957')
            if a.mode=='stop':
                # Real STOP is a held level. A pre-proven op9 can complete without
                # a service poll; observe the following idle poll and quiet entry too.
                s=once(s,'local function loaded()', 'local stop739,quiet739=false,false\nlocal function loaded()')
                s=once(s,' if pb(0)==7 then tile=tilePayload',
                       ' if pw(8)==957 and pb(0)==9 then stop739=true end\n if pb(0)==7 then tile=tilePayload')
                s=once(s,' if a==0x6001 then'," if a==0x6001 then\n  if stop739 then return 128 end")
                watch=f"checkedMem527(function() if stop739 and rd(0x1236)==1 then quiet739=true end end,emu.callbackType.exec,{labels['quiet']})\n"
                s=once(s,"checkedMem527(function()sample516('seal')",watch+"checkedMem527(function()sample516('seal')")
                s=once(s,'if (rejected or index>TOTAL)and not packet','if (quiet739 or rejected or index>TOTAL)and not packet')
                s=once(s,"assert(not rejected==(MODE=='normal'),'unexpected reject')",
                       "assert((quiet739 or rejected) and stop739 and word(0x14d0)==0 and word(0x14d4)==0)")
                s=once(s,'  if rejected then\n   local screen=', '  if rejected or quiet739 then\n   local screen=')
            else:
                # Damage only op9's previous display serial. Leave queue sequence and admission unchanged.
                s=once(s,' if pb(0)==7 then tile=tilePayload',""" if pw(8)==957 and pb(0)==9 then
  packet=packet:sub(1,128)..string.char(pb(128)~1)..packet:sub(130)
 end
 if pb(0)==7 then tile=tilePayload""")
            expected="(lastStatus==0xe4 or (quiet739 and lastStatus==0))" if a.mode=='stop' else "lastStatus==0xe0"
            s=once(s,'  assert(captured==commits)',f"  assert(({expected}) and word(0x1248)==52 and word(0x124a)==0)\n  assert(captured==commits)")
        return s

    with patch.object(replay,'observe',observe):
        if not negative:
            replay.run(a,edit_script=edit)
            return
        try:
            replay.run(a,edit_script=edit)
        except AssertionError:
            # The normal-replay helper insists on 53 commits. This run must terminate after 52.
            result=json.loads((a.out/'result.json').read_text())
            assert not (a.out/'map-error.txt').exists() and not (a.out/'callback-error.txt').exists()
            assert result['passed'] and result['commits']==52
            assert result['last_status'] in ((0,228) if a.mode=='stop' else (224,))
            assert sha(a.out/'retained.rgb')==sha(a.trace/'frame-956.rgb')
        else:
            raise AssertionError('957 fault was accepted')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','out','mesen','client'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=('trace','stop','stale'),default='trace')
    run(p.parse_args())
