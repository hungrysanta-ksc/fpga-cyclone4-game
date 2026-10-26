# SPDX-License-Identifier: MIT
"""Actual unchanged372 ARM and373 source/plan ABI on host context375."""
import json,shutil
import probe_nes_dual373 as previous
from nes_context375 import materialize,COMMON
from nes_delta231 import ROOT,sha
engine=previous.engine;old_prepare=engine.prepare
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];materialize(d)
 p=d/'joint266_tb.sv';s=p.read_text().replace('$bits(dut.flow.active305)!=121','$bits(dut.flow.active305)!=89')
 s=s.replace(' task clear_output;',"""
 reg [83:0] last_admitted375=0;
 always @(posedge host_clk)begin
  if(reset||source_fault)last_admitted375<=dut.flow.admitted286;
  else begin
   if(dut.flow.have_identity&&dut.flow.state!=dut.flow.DONE&&dut.flow.admitted286!==last_admitted375)
    $fatal(1,"CDC context changed during active display375");
   last_admitted375<=dut.flow.admitted286;
  end
  if(!reset&&!source_fault)begin
   if((dut.flow.ctx_header_busy375||dut.flow.ctx_check_busy375)&&!dut.flow.qr)$fatal(1,"shared context lost immutable queue head375");
   if(dut.init278&&dut.core.ram_b_addr>=716&&dut.core.ram_b_addr<=767)$fatal(1,"validator read/write entered reserved52B375");
   if(dut.core.ctx_write375)begin
    if(!dut.init278||dut.core.ctx_address375>=52)$fatal(1,"context before init/outside52B375");
    if(dut.core.ram_b_we&&dut.core.ctx_absolute375==dut.core.ram_b_addr)$fatal(1,"context/validator port collision375");
    $fwrite(events261,"context_store375,%0d,%0d,%0d,%0t\\n",f,dut.core.ctx_address375,dut.core.ctx_data375,$time);
   end
   if(dut.flow.ctx_check_busy375&&dut.flow.owner==dut.flow.MAP&&dut.flow.allocate)$fatal(1,"token changed during comparison375");
   if(dut.flow.read359[33]&&dut.flow.ctx_check_busy375)$fatal(1,"cold RAM token fetch during actual read375");
   if(dut.flow.state==dut.flow.DMA&&!dut.flow.data_command278&&!dut.flow.token_verified375)$fatal(1,"DMA before cold token verify375");
   if(dut.flow.ctx_check_done375)$fwrite(events261,"context_check375,%0d,%0d,%0d,%0t\\n",f,dut.flow.owner,dut.flow.allocation,$time);
  end
 end
 task clear_output;""")
 p.write_text(s,newline='\n')
 for n in COMMON:
  if n not in src:src.append(n)
  pins['shared375/'+n]=sha(d/n)
 for n in ('nes_context375.py','probe_nes_context375.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
 (d/'manifest375.json').write_text(json.dumps(dict(shared_boundary={n:sha(d/n) for n in COMMON}),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
