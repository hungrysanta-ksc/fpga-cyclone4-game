# SPDX-License-Identifier: MIT
"""Actual65816 receive-time append plus private C batch order; no full ARM/FPGA."""
import inspect
import measure_nes_dma247 as baseline
from nes_delta231 import once

OBSERVE=r'''
local orderphase247=assert(io.open(OUT_DIR..'/order-phase247.csv','w'))
orderphase247:write('generation,event,master_clock\n')
local function orderphasehook247(name)
 local st=emu.getState();orderphase247:write(string.format('%d,%s,%d\n',pw(8),name,st.masterClock));orderphase247:flush()
 if name=='coverage_return247' then
  local f=assert(io.open(OUT_DIR..'/commands-'..pw(8)..'.csv','w'));f:write('source,destination,bytes\n')
  for i=0,word(0x1250)-1,8 do f:write(string.format('%d,%d,%d\n',word(0x4000+i),word(0x4002+i),word(0x4004+i)))end;f:close()
 end
end
'''


def main():
    s=inspect.getsource(baseline.main)
    s=once(s,"p.add_argument('--rom', type=Path, required=True)","p.add_argument('--rom', type=Path, required=True)\n    p.add_argument('--client', type=Path, required=True)\n    p.add_argument('--host', type=Path, required=True)")
    s=once(s,"labels = json.loads((old/'client/labels.json').read_text())","client=a.client.resolve();host=a.host.resolve()\n    labels = json.loads((client/'labels.json').read_text())")
    s=s.replace("old/'client/sink165.sfc'","client/'sink165.sfc'").replace("old/'client/labels.json'","client/'labels.json'").replace("old/'common/host.exe'","host/'host.exe'")
    s=once(s,"    # Insert after helpers",'''    body=(client/'body.bin').read_bytes();base=0x7e2000
    for name,target_name in [('mark_return247','mark212'),('coverage_return247','coverage212')]:
        target=labels[target_name]&65535;needle=bytes((0x20,target&255,target>>8))
        hits=[i for i in range(len(body)-2) if body[i:i+3]==needle];assert len(hits)==1,hits
        labels[name]=base+hits[0]+3
    injection+=OBSERVE
    for name in ('mark212','mark_return247','coverage212','coverage_return247'):
        injection+='emu.addMemoryCallback(function()orderphasehook247('+json.dumps(name)+')end,emu.callbackType.exec,'+str(labels[name])+')\\n'
    # Insert after helpers''')
    s=once(s,"new_product_code=False,script_sha256","new_product_code=False,diagnostic_batch_order=True,script_sha256")
    ns=dict(baseline.__dict__);ns.update(OBSERVE=OBSERVE,__file__=__file__,__doc__=__doc__)
    exec(compile(s,'batchorder247-replay','exec'),ns);ns['main']()


if __name__=='__main__':main()
