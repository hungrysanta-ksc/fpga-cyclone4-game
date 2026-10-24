# SPDX-License-Identifier: MIT
"""Retained44 independent receipt/STOP guards on common ingress/decoder."""
import guard_nes_record305 as old
from nes_ingress307 import apply
from nes_delta231 import once

original=old.record305
def patch(d):original(d);apply(d)
old.record305=patch
original_observe=old.observe305
def observe(s):
    s=original_observe(s).replace('[106:0] link270','[109:0] link270').replace('[107:0]','[109:0]')
    return once(s,' initial begin : result264', '''
 initial begin : compressed307
  if(GNEG>=70&&GNEG<=74)begin
   wait(dut.flow.header[0]==15&&dut.core.validator.state==dut.core.validator.E_READ298&&dut.core.validator.packet_at298==40);
   @(negedge host_clk);injected264=1;
   force dut.core.validator.exec_op298=4;
   if(GNEG==70)force dut.core.validator.exec_data298=0;
   else begin
    force dut.core.validator.packet_at298=41;
    if(GNEG==71)begin force dut.core.validator.cursor=165;force dut.core.validator.exec_data298=8'h81;end
    if(GNEG==72)begin force dut.core.validator.exec_length298=42;force dut.core.validator.exec_data298=8'h7f;end
    if(GNEG==73)begin force dut.core.validator.exec_length298=42;force dut.core.validator.exec_data298=8'h80;end
    if(GNEG==74)force dut.core.validator.exec_data298=8'hff;
    if(GNEG==73||GNEG==74)begin
     @(posedge host_clk);@(posedge host_clk);@(negedge host_clk);force dut.core.validator.packet_at298=42;
    end
   end
   if(GNEG==74)begin
    wait(dut.core.validator.state==dut.core.validator.E_ZERO298);
    @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;test_abort=1;
    #2000;if(dut.exec_busy298||dut.exec_done298||dut.core.ram_b_we||v_sealed||bus_valid)$fatal(1,"STOP left RLE executor active");
   end else begin wait(source_fault);if(dut.core.validator.fault!=3)$fatal(1,"compressed bound wrong fault");end
  end
 end
 initial begin : result264''')
old.observe305=observe
engine=old.old.old.old.old
original_adapt=engine.adapt
def adapt(s):return original_adapt(s).replace('[106:0] link270','[109:0] link270').replace('[107:0]','[109:0]')
engine.adapt=adapt
original_run=engine.prior.run
def run(tool,args,d,label,*extra,**kw):
    if label=='vlog':
        tb=(d/'joint266_tb.sv').read_text()
        assert '[109:0] link270' in tb and '[107:0] link270' not in tb,'final fixture link width'
    return original_run(tool,args,d,label,*extra,**kw)
engine.prior.run=run
engine.CASES.update({70:'requirements codec rejected',71:'requirements run overflow',72:'truncated requirements literal',73:'requirements exact-length underflow',74:'STOP in requirements zero run'})
if __name__=='__main__':old.main()
