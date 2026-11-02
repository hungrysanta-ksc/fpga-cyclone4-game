# SPDX-License-Identifier: MIT
"""Read the actual 65816 accumulator at the final CMP #247 on the paired PUSH timeline."""
import argparse
import json
from pathlib import Path
import replay_nes_map527 as replay
from replay_nes_receipt548 import observe
from nes_raw506 import once


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.frames=53
    body=(a.client/'body.bin').read_bytes()
    labels=json.loads((a.client/'labels.json').read_text())
    prefix=bytes.fromhex('e220ad2410')
    assert body.count(prefix)==1
    start=body.index(prefix)
    gate=body[start:start+labels['fresh516']-labels['wait_final516']]
    compare=bytes.fromhex('c9f7')
    assert gate.count(compare)==1 and gate[gate.index(compare)+2]==0xb0
    pc=labels['wait_final516']+gate.index(compare)
    def edit(lua):
        return once(lua,'local function loaded()',f"""local gate550=assert(io.open(ROOT..'/gate550.csv','w'))
gate550:write('generation,clock,latched_v\\n')
emu.addMemoryCallback(function()
 if packet and pb(0)==3 then
  local state=emu.getState()
  gate550:write(string.format('%d,%d,%d\\n',pw(8),state.masterClock,state['cpu.a']&255))
  gate550:flush()
 end
end,emu.callbackType.exec,{pc})
local function loaded()""")
    replay.observer=observe
    replay.run(a,edit_script=edit)
