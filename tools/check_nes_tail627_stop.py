# SPDX-License-Identifier: MIT
"""Sample STOP at three accepted-section boundaries in the reordered 951 stream."""
import argparse
import json
from pathlib import Path

from check_nes_prelude554_stop import cancel
from nes_raw506 import once
from test_nes_seal538_stop import exercise


def run(args):
    args.out=args.out.resolve()
    args.out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((args.client/'labels.json').read_text())
    results=[]
    for offset in (1187,1505,1748):
        def stop(lua):
            lua=once(cancel(lua,labels,5),'pb(1)==5 and pw(10)>0',f'pb(1)==5 and pw(10)=={offset}')
            # Short literals can retire before service samples STOP. In that
            # case the real CPU enters quiet without an owned packet to reject.
            lua=once(lua,'local function loaded()',f"""local idle627=false
mem554(function()
 if sampled554 and not rejected then
  assert(not packet and lastStatus==0 and rd(0x1236)~=0,'STOP ownership')
  local last=requests[retired]
  assert(last and last:byte(2)==5 and string.unpack('<I2',last,9)==FAULT and
         string.unpack('<I2',last,11)=={offset},'retired different head')
  idle627=true;rejected=true;shown=emu.getState().frameCount
  local f=assert(io.open(ROOT..'/idle-stop.txt','w'));f:write(retired);f:close()
 end
end,emu.callbackType.exec,{labels['quiet']})
local function loaded()""")
            return once(lua,'sampled554 and lastStatus==0xe4 and word(0x125a)==0',
                        'sampled554 and ((idle627 and lastStatus==0) or (lastStatus==0xe4 and word(0x125a)==0))')
        row=exercise(args,951,f'section5-{offset}',edit_packet_case=stop,idle_witness='idle-stop.txt')
        row['idle_after_retire']=row['status']==0
        results.append(row)
    results.append(exercise(args,951,'final212'))
    (args.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('client','trace','mesen','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
