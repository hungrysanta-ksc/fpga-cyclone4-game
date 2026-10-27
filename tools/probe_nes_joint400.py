# SPDX-License-Identifier: MIT
"""400 fixed receiver/read owner + receive-ahead + native header DMA.

Actual M4 instruction/SPI/IRQ timeline; native 65816 component service,
not a resident CPU or physical pin timing proof.
"""
import inspect,json
import probe_nes_overlap400_live as overlap
import probe_nes_joint398 as previous
from nes_joint398 import rtl
from nes_fixed400 import apply,hint_top
from nes_delta231 import once,sha

driver=previous.prior.old
def current_rtl(d):rtl(d);apply(d)
driver.apply_rtl=current_rtl
driver.__file__=__file__

# Keep the existing actual native event offsets. A read still holds /RD low
# for 200 ns; no extra 200 ns idle is inserted between the native 8-master-
# clock header DMA beats. This is a bus model, not board pin signoff.
adapt=driver.adapt_tb
def current_tb(s):
 s=adapt(s)
 a=s.index(' task source_job394;');b=s.index(' endtask',a)
 s=s[:a]+s[a:b].replace('rd261(a,b);','rd400(a,b);')+s[b:]
 task=''' task rd400(input[23:0]a,output[7:0]b);begin
  @(negedge host_clk);bus_address=a;bus_read=0;#200;
  if(!bus_valid)$fatal(1,"400 native read unavailable address%h",a);
  b=bus_out;bus_read=1;
 end endtask
'''
 return s.replace(' task source_job394;',task+' task source_job394;')
driver.adapt_tb=current_tb

# The inherited preparation also runs the protocol preflight on this same
# licensed server. Bind its new tag port and include the actual read owner.
s=inspect.getsource(previous.fresh)
s=s.replace("['nes_byte398.sv']","['nes_byte398.sv','nes_read_owner400.sv']")
s=once(s,' import json\n'," q.write_text(hint_top400(q.read_text()),newline='\\n')\n import json\n")
s=s.replace('probe_nes_hint398.py','probe_nes_fixed400_hint.py')
s=s.replace("d/'manifest398.json'","d/'manifest400.json'")
s=s.replace('dut.flow.queue.event_count','dut.flow.queue.count270').replace('dut.flow.queue.event_end','dut.flow.queue.link270[112]').replace('dut.flow.queue.event_flags',"8'd0")
ns=dict(previous.__dict__,hint_top400=hint_top)
exec(compile(s,'joint400-prepare','exec'),ns)
driver.prepare=ns['fresh']
if __name__=='__main__':driver.main()
