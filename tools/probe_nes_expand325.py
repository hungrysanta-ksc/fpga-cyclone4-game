# SPDX-License-Identifier: MIT
import shutil
import probe_nes_owner319 as old
from nes_expand325 import apply
from nes_delta231 import ROOT,sha,once
previous=old.engine.prepare

def prepare(*args,**kwargs):
 src,pins=previous(*args,**kwargs);d=args[0];apply(d)
 p=d/'joint266_tb.sv';s=p.read_text()
 s=once(s,'if(read267!=n267-16)$fatal','if(read267!=dut.flow.chunk_length)$fatal')
 s=once(s,"if(bus_address>=24'h400800&&bus_address<=24'h4008ff)begin ignore267=call263(1,16+read267,byte267);read267++;end", """if(bus_address>=24'h400800&&bus_address<24'h401800)begin
     if(read267<n267-16)ignore267=call263(1,16+read267,byte267);
     read267++;
    end""")
 s=once(s,' task clear_output;',r'''
 integer stage_frame325=0,expand_ticks325=0,tile_block325=0,ready_ticks325=0;
 always @(posedge host_clk)if(!reset&&active263&&!source_fault)begin
  if(stage_frame325!=f)begin stage_frame325=f;expand_ticks325=0;tile_block325=0;ready_ticks325=0;end
  if(dut.flow.state==dut.flow.EXPAND325)expand_ticks325++;
  if(dut.flow.trequest&&dut.flow.owner!=dut.flow.TILE)tile_block325++;
  if(dut.flow.chunk_ready)ready_ticks325++;
  if(dut.flow.owner==dut.flow.MAP&&dut.flow.shared_ram.aperture.filling&&dut.flow.chunk_ready)$fatal(1,"staging write/read ownership overlap325");
 end
 task clear_output;''')
 s=once(s,'  $fwrite(events261,"consumer,',r'''  $fwrite(events261,"stage325,%0d,%0d,%0d,%0d\n",f,expand_ticks325,tile_block325,ready_ticks325);
  $fwrite(events261,"consumer,''')
 p.write_text(s,newline='\n')
 for n in ('nes_expand325.py','probe_nes_expand325.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
old.engine.prepare=prepare
old.engine.__file__=__file__
if __name__=='__main__':old.engine.main()
