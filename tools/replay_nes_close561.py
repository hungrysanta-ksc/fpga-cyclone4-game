# SPDX-License-Identifier: MIT
"""Observe the final aperture read and validated token write on the replayed 65816."""
from functools import partial
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from replay_nes_admit556 import admission,frontier,observe,replay
from nes_raw506 import once


def bank_events(script,labels,all_banks=False):
    script=admission(script,labels)
    script=once(script,'local function loaded()',r"""local bank561=assert(io.open(ROOT..'/bank561.csv','w'))
bank561:write('index,slot,bytes,token,event,clock\n')
local function stamp561(event)
 if packet and pb(0)==7 and pw(8)==952 then
  bank561:write(string.format('%d,%d,%d,%d,%s,%d\n',index,pw(10),pw(14),pw(16)+65536*pw(18),event,emu.getState().masterClock))
  bank561:flush()
 end
end
local function loaded()""")
    script=once(script,'reads=reads+1;return tile:byte(i+1)',
                "reads=reads+1;if reads==#tile then stamp561('last_read')end;return tile:byte(i+1)")
    if all_banks:
        script=once(script,"pb(0)==7 and pw(8)==952 then\n  bank561","pb(0)==7 then\n  bank561")
        script=once(script,"assert(tile,'unowned descriptor');","if a==0x6040 then stamp561('descriptor')end;assert(tile,'unowned descriptor');")
        script=once(script,"if a<0x6050 then token[a-0x604c+1]=v else",
                    "if a<0x6050 then stamp561('token'..(a-0x604c));token[a-0x604c+1]=v else")
    guard="for i=1,4 do assert(token[i]==pb(15+i),'receipt token')end"
    return once(script,guard,guard+";stamp561('consume')")


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--all-banks',action='store_true')
    for k in ('client','trace','mesen','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.frames=53
    labels=json.loads((a.client/'labels.json').read_text())
    limit=json.loads((a.client/'build.json').read_text())['map_chunk_B']
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit=str(limit))),patch.object(replay,'observer',observe):
        replay.run(a,edit_script=lambda s:bank_events(s,labels,a.all_banks))
