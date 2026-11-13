# SPDX-License-Identifier: MIT
"""Inject a held STOP at each transmitted raw row of the sealed 957 patch."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from nes_raw506 import once, sha


def check(a):
    original=replay.run
    def guarded(args,*,edit_script):
        def edit(script):
            script=once(edit_script(script),'if pw(8)==957 and pb(0)==9 then stop739=true end','')
            pc=json.loads((args.client/'labels.json').read_text())[f'row624_{a.row}']
            hook=f"""checkedMem527(function()
 if packet and pw(8)==957 and pb(0)==3 and word(0x78)==0x1d then
  stop739=true
  local f=assert(io.open(ROOT..'/raw-stop.txt','w'));f:write(emu.getState().masterClock);f:close()
 end
end,emu.callbackType.exec,{pc})
"""
            return once(script,'local function loaded()',hook+'local function loaded()')
        return original(args,edit_script=edit)
    a.mode='stop'
    with patch.object(replay,'run',guarded):
        owner.run(a)
    return verify(a)


def verify(a):
    import csv
    successful=json.loads((a.out/'result.json').read_text())
    assert successful['commits']==52 and successful['last_status']==0xe4
    assert sha(a.out/'retained.rgb')==sha(a.trace/'frame-956.rgb')
    tick=int((a.out/'raw-stop.txt').read_text())
    with (a.out/'window.csv').open() as stream:
        rows=[r for r in csv.DictReader(stream) if r['g']=='957' and int(r['clock'])>=tick]
    assert not any(r['event'] in ('ppu_dma','reveal') for r in rows)
    assert [int(r['value']) for r in rows if r['event']=='ack' and r['op']=='3']==[0xe4]
    return dict(row=a.row,tick=tick,previous_image=sha(a.out/'retained.rgb'),trace=sha(a.out/'window.csv'),
                commits=52)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('trace','out','client','mesen'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--row',type=int,choices=(0,2),required=True)
    p.add_argument('--verify-existing',action='store_true')
    a=p.parse_args()
    result=verify(a) if a.verify_existing else check(a)
    (a.out/'guard754.json').write_text(json.dumps(result)+'\n')
