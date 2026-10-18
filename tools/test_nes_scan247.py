# SPDX-License-Identifier: MIT
"""P1 scanner boundary replay: actual65816 plus existing independent232 checks.

No charge-policy change, no FPGA/ARM integration or physical FPS claim.
"""
from pathlib import Path
import inspect
import measure_nes_dma247 as baseline
from nes_delta231 import once

OBSERVE=r'''
local scan247active=nil
local scan247last=nil
local scan247max=0
local scan247visits=0
local phase247=assert(io.open(OUT_DIR..'/phase247.csv','w'))
phase247:write('generation,event,master_clock,scanline,hclock,service_visits,max_service_gap\n')
local function phasehook247(name)
 local st=emu.getState()
 if name=='scan247' then scan247active=st.masterClock;scan247last=st.masterClock;scan247max=0;scan247visits=0 end
 if name=='scan_service247' and scan247active then
  scan247max=math.max(scan247max,st.masterClock-scan247last);scan247last=st.masterClock;scan247visits=scan247visits+1
  return
 end
 if name=='scan_return247' then
  assert(scan247active);scan247max=math.max(scan247max,st.masterClock-scan247last)
  local f=assert(io.open(OUT_DIR..'/commands-'..pw(8)..'.csv','w'));f:write('source,destination,bytes\n')
  for i=0,word(0x1250)-1,8 do f:write(string.format('%d,%d,%d\n',word(0x4000+i),word(0x4002+i),word(0x4004+i)))end
  f:close();scan247active=nil
 end
 phase247:write(string.format('%d,%s,%d,%d,%d,%d,%d\n',pw(8),name,st.masterClock,st['ppu.scanline'],st['ppu.hClock'] or -1,scan247visits,scan247max));phase247:flush()
 if name=='scan247' and pw(8)==1 then
  local f=assert(io.open(OUT_DIR..'/state-keys.txt','w'));for k,v in pairs(st)do f:write(tostring(k)..'='..tostring(v)..'\n')end;f:close()
 end
end
'''


def main():
    s=inspect.getsource(baseline.main)
    s=once(s,"p.add_argument('--rom', type=Path, required=True)","p.add_argument('--rom', type=Path, required=True)\n    p.add_argument('--client', type=Path, required=True)")
    s=once(s,"labels = json.loads((old/'client/labels.json').read_text())","client=a.client.resolve()\n    labels = json.loads((client/'labels.json').read_text())")
    s=once(s,"str(old/'client/sink165.sfc')","str(client/'sink165.sfc')")
    s=once(s,"old/'client/sink165.sfc',old/'client/labels.json'","client/'sink165.sfc',client/'labels.json'")
    s=once(s,"    # Insert after helpers",'''    body=(client/'body.bin').read_bytes();base=0x7e2000
    target=labels['scan247']&65535
    needle=bytes((0x20,target&255,target>>8))
    hits=[i for i in range(len(body)-2) if body[i:i+3]==needle]
    assert len(hits)==1,hits
    labels['scan_return247']=base+hits[0]+3
    injection+=OBSERVE
    for name in ('scan247','scan_service247','scan_return247','transfer212','final_upload212_return','wait169'):
        injection+='emu.addMemoryCallback(function()phasehook247('+json.dumps(name)+')end,emu.callbackType.exec,'+str(labels[name])+')\\n'
    # Insert after helpers''')
    s=once(s,"new_product_code=False,script_sha256", "new_product_code=False,diagnostic_scanner=True,script_sha256")
    ns=dict(baseline.__dict__);ns.update(OBSERVE=OBSERVE,__file__=__file__,__doc__=__doc__)
    exec(compile(s,'scan247-replay','exec'),ns);ns['main']()


if __name__=='__main__':main()
