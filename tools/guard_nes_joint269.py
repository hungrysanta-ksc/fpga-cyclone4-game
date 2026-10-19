# SPDX-License-Identifier: MIT
"""Retain38 semantic/receipt guards and check readable sticky fault status."""
import inspect
import guard_nes_joint266 as previous
import guard_nes_joint265 as old
from probe_nes_joint266 import prepare as base_prepare
from probe_nes_refill269 import patch
from nes_delta231 import once


def prepare(d,last):
 src,pins,stats=base_prepare(d,last);patch(d,src,pins);return src,pins,stats


def main():
 # Reuse the complete266 guard generator, with a modified main source object.
 s=inspect.getsource(old.main)
 s=once(s,' reg [7:0] frozen[0:1023];',' reg [7:0] frozen[0:1023];reg [7:0] status269;')
 s=once(s,'  wait(source_fault);disable bus263;repeat(4)@(negedge clk);', '''  wait(source_fault);disable bus263;bus_read=1;bus_write=1;repeat(8)@(negedge clk);
  rd261(24'h006001,status269);
  if(status269[7:6]!=2'b11)$fatal(1,"fault status not readable/sticky");
  wr261(24'h006006,8'ha5);
  rd261(24'h006001,status269);
  if(status269[7:6]!=2'b11)$fatal(1,"invalidation cleared during STOP");
  bus_address=24'h006000;bus_read=0;#100;
  if(bus_valid)$fatal(1,"ordinary bus open during fault");bus_read=1;
  wr261(24'h00601c,8'ha5);
  if(dut.flow.queue.retired!=0)$fatal(1,"stale ACK retired queue");''')
 # inspect.getsource on a generated function cannot recover text. Substitute
 # only this one read in266's generator, preserving every existing guard.
 outer=inspect.getsource(previous.main)
 outer=once(outer,'inspect.getsource(old.main)','guard_source')
 ns=dict(previous.__dict__);ns.update(guard_source=s,prepare=prepare,__file__=__file__)
 exec(compile(outer,'guard269-outer','exec'),ns);ns['main']()


if __name__=='__main__':main()
