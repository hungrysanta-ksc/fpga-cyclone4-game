# SPDX-License-Identifier: MIT
"""Execute complete mask8 receiver, independent WRAM/VRAM oracle and timings."""
import inspect
import measure_nes_dma247 as baseline
from nes_delta231 import once

OBSERVE=r'''
local phase247=assert(io.open(OUT_DIR..'/mask-phase247.csv','w'))
phase247:write('generation,event,master_clock\n')
local function phasehook247(name)
 phase247:write(string.format('%d,%s,%d\n',pw(8),name,emu.getState().masterClock));phase247:flush()
 if name=='coverage_return247' then
  local f=assert(io.open(OUT_DIR..'/commands-'..pw(8)..'.csv','w'));f:write('source,destination,bytes\n')
  for i=0,word(0x1250)-1,8 do f:write(string.format('%d,%d,%d\n',word(0x4000+i),word(0x4002+i),word(0x4004+i)))end;f:close()
 end
end
'''

CHECK=r'''
  if ack[1]==0 and pb(0)==9 then
   local at=17;assert(pb(16)==2)
   while at<#packet do
    local group=pb(at);local mask=pb(at+1);at=at+2
    assert(rd(0x1500+group)==mask,'word receipt mismatch')
    for bit=0,7 do if (mask&(1<<bit))~=0 then
     local dst=0x15000+word(0x1020)+group*16+bit*2
     assert(rd(dst)==pb(at) and rd(dst+1)==pb(at+1),'mask staging mismatch');at=at+2
    end end
   end
   assert(at==#packet)
  end
  if ack[1]==0 and pb(0)==10 then assert(word(0x1490)==pw(10)+pw(12),'manifest cursor mismatch')end
  if ack[1]==1 then assert(rd(0x148c+word(0x1034))==1,'missing map initialization')end
'''

def main():
 s=inspect.getsource(baseline.main)
 s=once(s,"p.add_argument('--rom', type=Path, required=True)","p.add_argument('--rom', type=Path, required=True)\n    p.add_argument('--client', type=Path, required=True)\n    p.add_argument('--host', type=Path, required=True)")
 s=once(s,"labels = json.loads((old/'client/labels.json').read_text())","client=a.client.resolve();host=a.host.resolve()\n    labels = json.loads((client/'labels.json').read_text())")
 s=s.replace("old/'client/sink165.sfc'","client/'sink165.sfc'").replace("old/'client/labels.json'","client/'labels.json'").replace("old/'common/host.exe'","host/'host.exe'")
 s=once(s,'    # Insert after helpers', '''    body=(client/'body.bin').read_bytes();base=0x7e2000
    injection+=OBSERVE
    for name in ('mark212','coverage212','mask247','manifest247'):
        target=labels[name]&65535;needle=bytes((0x20,target&255,target>>8))
        hits=[i for i in range(len(body)-2) if body[i:i+3]==needle];assert len(hits)==1,(name,hits)
        ret=name.replace('212','').replace('247','')+'_return247';labels[ret]=base+hits[0]+3
        for event in (name,ret):injection+='emu.addMemoryCallback(function()phasehook247('+json.dumps(event)+')end,emu.callbackType.exec,'+str(labels[event])+')\\n'
    lua=once(lua,'  if pb(0)==7 then\\n',CHECK+'  if pb(0)==7 then\\n')
    # Insert after helpers''')
 s=once(s,'new_product_code=False,script_sha256','new_product_code=False,diagnostic_mask8=True,script_sha256')
 ns=dict(baseline.__dict__);ns.update(OBSERVE=OBSERVE,CHECK=CHECK,once=once,__file__=__file__,__doc__=__doc__)
 exec(compile(s,'maskrun247-replay','exec'),ns);ns['main']()

if __name__=='__main__':main()
