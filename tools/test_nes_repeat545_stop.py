# SPDX-License-Identifier: MIT
"""Interrupt the actual uniform-fill loop before, between and after chunks."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_seal538_stop import exercise


def inject(source, address, length, boundary):
    source=once(source, 'local function loaded()', f"""local fill545={{done=0,stop=false}}
local function target545()
 return packet and pw(8)==FAULT and pb(0)==4 and pb(1)==5 and pw(14)=={length} and pb(16)==pb(17)
end
emu.addMemoryCallback(function()
 if not target545() then return end
 fill545.armed=true
 if not fill545.saved then
  fill545.base=0x10000+word(0x1020)+0x6500+pw(10)
  fill545.saved={{}}
  for i=0,{length}-1 do fill545.saved[i]=rd(fill545.base+i) end
 end
end,emu.callbackType.exec,{address})
local function loaded()""")
    source=once(source, 'if a==0x6001 then', f"""if a==0x6001 then
  if target545() and fill545.armed and fill545.done=={boundary} then
   fill545.stop=true
   for i=0,{length}-1 do assert(rd(fill545.base+i)==(i<fill545.done and pb(16) or fill545.saved[i])) end
   return 128
  end""")
    source=once(source, 'if a>=0x4300 and a<=0x4306 then', f"""if target545() and a==0x420b then
  assert(not fill545.stop and fill545.armed and v==1 and regs[0x4300]==8 and regs[0x4301]==0x80)
  local n=regs[0x4305]+256*regs[0x4306]
  assert(n==math.min(64,{length}-fill545.done));fill545.done=fill545.done+n
 end
 if a>=0x4300 and a<=0x4306 then""")
    return once(source, "assert(lastStatus==0xe4,'STOP status')",
                f"assert(fill545.stop and fill545.done=={boundary} and lastStatus==0xe4,'fill STOP status')")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('client','trace','mesen','out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args=parser.parse_args()
    args.out=args.out.resolve()
    args.out.mkdir(parents=True,exist_ok=False)
    address=json.loads((args.client/'labels.json').read_text())['zero_chunk516']
    rows=[]
    for gen,length in ((906,194),(907,66)):
        for boundary in [*range(0,length,64),length]:
            def edit(source):
                return inject(source,address,length,boundary)
            rows.append(exercise(args,gen,f'fill{length}-stop{boundary}',edit_packet_case=edit))
    (args.out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
