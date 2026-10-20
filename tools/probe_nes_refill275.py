# SPDX-License-Identifier: MIT
"""Actual inline ARM -> SPI queue -> descriptor-bound reference executor.

Retained actual ordinary65816 traces read the identical logical packet view.
Refill/IRQ bodies and synthetic tile ROM competition use the existing267
schedule. Map/tile/final display remain bus modeled, not physical60fps proof.
"""
import inspect,shutil
import probe_nes_refill274 as prior
import probe_nes_refill267 as old
from probe_nes_inline275 import build,verify
from nes_delta231 import ROOT,sha
from nes_joint275 import patch

def prepare(*args,**kwargs):
 src,pins=prior.prepare(*args,**kwargs);d=args[0];patch(d)
 p=d/'joint266_tb.sv';s=p.read_text()
 s=s.replace('$fatal(1,"joint261 flow/lease fault',
 '''begin $display("REF275 state=%0d op=%0d kind=%0d pos=%0d end=%0d cursor=%0d wire=%0d logical=%0d ins=%0d args=%0d,%0d,%0d left=%0d hash=%0d qfault=%0d",dut.flow.state,dut.flow.header[0],dut.flow.header[1],dut.flow.opos,dut.flow.oend,dut.flow.cursor,dut.flow.wire_length275,dut.flow.qlen,dut.flow.header[20],dut.flow.header[16],dut.flow.header[17],dut.flow.header[18],dut.flow.rle_left,dut.flow.rle_zero,dut.flow.qfault);$fatal(1,"joint261 flow/lease fault''')
 s=s.replace('flow_fault,lease_fault,dut.flow.state);','flow_fault,lease_fault,dut.flow.state);end')
 s=s.replace("dut.flow.queue.buffer[{dut.flow.queue.retired[1:0],8'd0}+i]",
             "dut.flow.queue.buffer[{dut.flow.queue.retired[1:0],8'd0}+i+(dut.flow.inline275?2:0)]")
 p.write_text(s,encoding='utf-8',newline='\n')
 for name in ['nes_inline275.py','nes_inline275.sv.inc','nes_joint275.py','probe_nes_inline275.py','probe_nes_refill275.py']:
  shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(ROOT/'tools'/name)
 return src,pins

def worker(*args,**kwargs):
 ns=dict(old.__dict__);ns.update(verify=verify)
 exec(compile(inspect.getsource(old.worker),'worker275','exec'),ns)
 return ns['worker'](*args,**kwargs)

def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,build=build,worker=worker,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'refill275-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
