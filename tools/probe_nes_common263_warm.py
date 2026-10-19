# SPDX-License-Identifier: MIT
"""Actual65816 warm907:7ranges/one batch after905/906 RTL history.

Earlier frames use the existing bus model. VRAM is seeded from the independently
verified905 bank image immediately before the first actual warm DMA. This is a
warm-state experiment, not continuous full-game65816 execution.
"""
import inspect,json
from nes_delta231 import once,ROOT,sha
import probe_nes_common263 as common
import probe_nes_joint261_coupled as old

def prepare(d,last):
 src,pins,stats=common.prepare(d,907)
 p=d/'joint262_tb.sv';s=p.read_text()
 s=once(s,'  if(!RPC&&!NEG&&(PRENEG==0||PRENEG==6))begin','  if(!NEG&&(PRENEG==0||PRENEG==6))begin') if '  if(!RPC&&!NEG' in s else once(s,' if(!RPC&&!NEG&&(PRENEG==0||PRENEG==6))begin',' if(!NEG&&(PRENEG==0||PRENEG==6))begin')
 s=once(s,'   if(dut.flow.state==dut.flow.DMA&&staged)begin','   if((!RPC||f<907)&&dut.flow.state==dut.flow.DMA&&staged)begin')
 s=once(s,'   end else if(v_sealed&&dut.flow.state==dut.flow.IDLE)begin','   end else if((!RPC||f<907)&&v_sealed&&dut.flow.state==dut.flow.IDLE)begin')
 s=once(s,'   target_waiting=1;','   target_waiting=(f==907);')
 p.write_text(s,encoding='utf-8',newline='\n');pins[(ROOT/'tools/probe_nes_common263_warm.py').as_posix()]=sha(ROOT/'tools/probe_nes_common263_warm.py')
 return src,pins,stats

def main():
 s=inspect.getsource(old.main)
 s=once(s,"p.add_argument('--out'", "p.add_argument('--cached',action='store_true');p.add_argument('--out'")
 s=s.replace('prepare(d,905);body=rom(d)','prepare(d,907);body=rom(d,a.cached)').replace('joint261_tb','joint262_tb').replace('+LAST=905','+LAST=907').replace('time.monotonic()+120','time.monotonic()+240')
 s=s.replace('scope=__doc__,cpu=cpu_result','scope=__doc__,cached=a.cached,warm_frame=907,cpu=cpu_result')
 lua=old.LUA.replace('0x6040,0x6052','0x6040,0x6053').replace('bytes==4096 and chunks==64','bytes==40 and chunks==7').replace("OUT..'/map905.expected'","OUT..'/map907.expected'")
 lua=lua.replace(' if a==0x6050 then', " assert(a~=0x6057,'CPU context validation failed')\n if a==0x6050 then")
 lua=once(lua,'if not dma_start then dma_start=emu.getState().masterClock end', '''if not dma_start then
 local f=assert(io.open(OUT..'/map905.expected','r'));local text=f:read('*a');f:close();local i=0
 for b in text:gmatch('%x%x')do emu.write(0x8000+i,tonumber(b,16),emu.memType.snesVideoRam);i=i+1 end
 assert(i==4096);dma_start=emu.getState().masterClock
end''')
 romsrc=inspect.getsource(common.rom);romsrc=once(romsrc,'c.emit(0xc9,1,0)','c.emit(0xc9,3,0)')
 rn=dict(common.__dict__);exec(compile(romsrc,'common263-warm-rom','exec'),rn)
 ns=dict(old.__dict__);ns.update(prepare=prepare,rom=rn['rom'],LUA=lua,TCL=old.TCL.replace('$n<1000','$n<3000'),__doc__=__doc__)
 exec(compile(s,'common263-warm-coupled','exec'),ns);ns['main']()

if __name__=='__main__':main()
