# SPDX-License-Identifier: MIT
"""Original ARM274 wire; unified source/query/descriptor/receipt FSM."""
import inspect,shutil
import probe_nes_refill274 as prior
import probe_nes_refill267 as old
from probe_nes_split274 import build,verify
from nes_delta231 import ROOT,sha,once
from nes_joint276 import patch

def prepare(*args,**kwargs):
 src,pins=prior.prepare(*args,**kwargs);d=args[0];patch(d)
 p=d/'joint266_tb.sv';s=p.read_text()
 s=once(s,'endmodule','''
 always @(posedge clk)if(!reset&&dut.desc_valid276&&dut.desc_ready276)
  if(!dut.core.output_phase||dut.core.encoder.q_pending||source_fault)
   $fatal(1,"descriptor276 source/query ownership collision");
endmodule''')
 s=s.replace('$fatal(1,"joint261 flow/lease fault',
 '''begin $display("CORE276 state=%0d fault=%0d active=%0d pending=%0d op=%0d at=%0d end=%0d manifest=%0d corecursor=%0d host=%0d",
 dut.core.encoder.state,dut.core.encoder.fault,dut.core.encoder.left_row,dut.core.encoder.q_normal,
 dut.core.encoder.header[0],dut.core.encoder.raw_at,dut.core.encoder.raw_limit,dut.core.encoder.spans,dut.core.encoder.cursor,dut.flow.state);
 $fatal(1,"joint261 flow/lease fault''')
 s=s.replace('flow_fault,lease_fault,dut.flow.state);','flow_fault,lease_fault,dut.flow.state);end')
 p.write_text(s,encoding='utf-8',newline='\n')
 for name in ['nes_joint276.py','probe_nes_refill276.py']:
  shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(ROOT/'tools'/name)
 return src,pins

def worker(*args,**kwargs):
 ns=dict(old.__dict__);ns.update(verify=verify)
 exec(compile(inspect.getsource(old.worker),'worker276','exec'),ns)
 return ns['worker'](*args,**kwargs)

def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,build=build,worker=worker,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'refill276-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
