# SPDX-License-Identifier: MIT
import os,shutil
os.environ['NES334_ARM_ONLY']='1'
os.environ['NES332_ARM_ONLY']='0'
os.environ['NES331_ARM_ONLY']='0'
os.environ['NES330_MAP']='1'
import probe_nes_execute334 as previous
from nes_read336 import apply,native
from nes_delta231 import ROOT,sha,once
engine=previous.engine
old_prepare=engine.prepare


def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    if os.environ.get('NES336_ARM_ONLY')!='1':
        apply(d)
        p=d/'joint266_tb.sv';s=p.read_text()
        s=once(s,'$bits(dut.flow.active305)!=145','$bits(dut.flow.active305)!=121')
        s=once(s,'''  if(dut.core.validator.state==dut.core.validator.V_RWRITE&&
     !dut.core.validator.v_mapmode&&!acked278)$fatal(1,"receipt before ordered ACK");''', '''  // Private writes are permitted only for a qualified read-owned job.
  if(dut.core.validator.ram_we&&(dut.core.validator.state==dut.core.validator.V_RWRITE||dut.core.validator.state==dut.core.validator.V_PWRITE))begin
   if(dut.flow.state!=dut.flow.DMA||dut.flow.tap_state278!=5||!dut.flow.chunk_ready)
    $fatal(1,"private write without active read job336");
  end
  if(dut.flow.consume_write&&dut.flow.good_consume)
   $fwrite(events261,"publish336,%0d,%0d,%0d,%0t\\n",f,dut.flow.chunk_token,dut.flow.read_count,$time);
  if((dut.flow.consume_record312||dut.flow.map_consume)&&
     (!acked336||!dut.flow.tap_idle278||dut.flow.read_pending336||!v_ready))
   $fatal(1,"publish before token or job drain336");
  if(dut.flow.ordinary_finish&&(!dut.flow.tap_idle278||dut.flow.read_pending336))
   $fatal(1,"final scan before job drain336");''')
        s=once(s,' reg acked278=0;', ''' reg acked278=0,acked336=0;
 always @(posedge host_clk)begin
  if(reset||dut.flow.state==dut.flow.CHECK||dut.flow.state==dut.flow.DCHECK)acked336<=0;
  else if(dut.flow.consume_write&&dut.flow.good_consume)acked336<=1;
 end''')
        s=once(s,' parameter integer ROM_WINDOW=0;', '''
 always @(posedge host_clk)if(!reset&&active263&&!source_fault)begin
  if(dut.flow.tap_capture278)
   $fwrite(events261,"read336,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\\n",f,dut.flow.chunk_token,dut.flow.header[0],dut.flow.header[1],dut.flow.tap_address278,dut.flow.read_count,dut.flow.aperture_data,$time);
  if(dut.core.validator.v_range_valid&&v_ready)
   $fwrite(events261,"unit336,%0d,%0d,%0d,%0d,%0t\\n",f,dut.flow.chunk_token,dut.core.validator.v_map_range,dut.core.validator.v_first,$time);
  if(dut.core.validator.ram_we&&(dut.core.validator.state==dut.core.validator.V_RWRITE||dut.core.validator.state==dut.core.validator.V_PWRITE))
   $fwrite(events261,"private336,%0d,%0d,%0d,%0d,%0t\\n",f,dut.flow.chunk_token,dut.core.validator.ram_addr,dut.core.validator.ram_w,$time);
 end
 parameter integer ROM_WINDOW=0;''')
        # CRC bits are now private writes. They must still be absent at their
        # own raw hash completion; earlier independent granules may be present.
        p.write_text(s,newline='\n')
    for name in ('nes_read336.py','probe_nes_read336.py'):
        shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(d/name)
    return src,pins


engine.prepare=prepare
if os.environ.get('NES336_RTL_ONLY')!='1':engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
