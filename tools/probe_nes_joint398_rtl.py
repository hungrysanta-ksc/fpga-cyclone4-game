# SPDX-License-Identifier: MIT
"""Common byte-program host against the complete source/receipt bus fixtures."""
import inspect
import probe_nes_joint396_rtl as previous
from nes_delta231 import ROOT
s=previous.s.replace("'nes_stage396.sv','nes_check396.sv'","'nes_stage396.sv','nes_check396.sv','nes_byte398.sv'")
s=s.replace('from guard_nes_joint396 import guards','from guard_nes_joint398 import guards')
s=s.replace("(d/'record_tb.sv').write_text(test396(),newline='\\n')", "shutil.copyfile(a.rtl/'program398.hex',d/'program398.hex');(d/'record_tb.sv').write_text(test398(),newline='\\n')")
def test398():
 s=previous.test396().replace('[113:0]','[153:0]')
 s=s.replace('nes_output260 flow(',"nes_output260 flow(.hint_metaactive398(1'b0),.hint_meta_at398(4'd0),")
 s=s.replace(' initial begin\n  repeat(4)', ' reg[7:0]protected398[0:799];\n initial begin\n  repeat(4)')
 s=s.replace('   active=1;feeding=1;', '''   if(GUARD==20)begin
    for(integer i=0;i<800;i++)protected398[i]=flow.tile_link.memory[i];
    force flow.mv=1'b1;force flow.mw=1'b1;force flow.ma=8'd224;force flow.md=8'ha5;
    repeat(2)@(negedge host_clk);
    for(integer i=0;i<800;i++)if(flow.tile_link.memory[i]!==protected398[i])$fatal(1,"context port wrapped into tile/stamps");
    release flow.mv;release flow.mw;release flow.ma;release flow.md;wait(1'b0);
   end
   active=1;feeding=1;''')
 s=s.replace('always @(negedge host_clk)begin','always @(negedge host_clk)begin\n  if(!reset&&!cancel&&flow.fault)$display("TRACE398 pc%0d handler%b qfault%b event%b kind%b count%0d value%h flags%b seq%0d bad%h",flow.debug_pc,flow.handler,flow.qfault,flow.queue.event_valid,flow.queue.event_end,flow.queue.event_count,flow.queue.event_value,flow.queue.event_flags,flow.queue.sequence312,flow.tile_link.memory[900]);',1)
 return s
ns=dict(previous.ns,test398=test398);exec(compile(s,'joint398-rtl','exec'),ns)
if __name__=='__main__':ns['main']()
