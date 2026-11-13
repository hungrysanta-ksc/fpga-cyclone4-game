# SPDX-License-Identifier: MIT
"""Inject STOP or a new head at the actual post-map grant on a live 745 calendar."""
import argparse
from unittest.mock import patch
from pathlib import Path
from nes_raw506 import once
import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from analyze_nes_owner739 import read, sha


def verify(a):
    labels=read(a.client/'labels.json')
    original=replay.run
    fault=a.fault
    a.mode='trace' if fault=='head' else 'stop'
    def retain(rows,actual):
        before=lambda rr:[r for r in rr if int(r['g'])<957]
        assert before(rows)==before(actual)
        return dict(matched_prefix=len(before(actual)))
    def run(args,*,edit_script):
        def augment(script):
            s=edit_script(script)
            if fault=='head':
                action="""assert(target522>st.masterClock and b522~='FINISH' and unhex(b522):byte(2)==5)
                target522=st.masterClock;rpc()"""
                point=labels['ready524']
            else:
                s=once(s,'if pw(8)==957 and pb(0)==9 then stop739=true end','-- STOP is supplied at the DMA boundary below')
                action='stop739=true'
                point=labels['priority524']
            check='word(0x1226)==957 and regs[0x4302]+256*regs[0x4303]==19104 and regs[0x4305]==64'
            hook=f"""local fired745=false
checkedMem527(function(a)
 if not fired745 and {check} then
  fired745=true;local st=emu.getState()
  local f=assert(io.open(ROOT..'/fault745.txt','w'));f:write(st.masterClock);f:close()
  {action}
 end
end,emu.callbackType.exec,{point})
"""
            if fault=='during':
                hook=once(hook,f'end,emu.callbackType.exec,{point})','end,emu.callbackType.write,0x2118)')
            return once(s,'local finished522=false',hook+'local finished522=false')
        return original(args,edit_script=augment,compare_trace=retain)
    with patch.object(replay,'run',run):
        owner.run(a)
    assert int((a.out/'fault745.txt').read_text())>0
    if fault!='head':
        assert sha(a.out/'retained.rgb')==sha(a.trace/'frame-956.rgb')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('client','mesen','trace','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--fault',choices=('pre','during','head'),required=True)
    verify(p.parse_args())
