# SPDX-License-Identifier: MIT
"""Retimed live ARM/SPI/ROM execution with sticky bank invalidation."""
import inspect
import probe_nes_refill267 as old
from nes_joint269 import sources
from nes_delta231 import once,sha
from pathlib import Path


def patch(d,src,pins):
 for n,s in sources().items():
  # Keep the ROM267 tile producer and board additions prepared by the caller.
  if n=='nes_mux260.sv':(d/n).write_text(s,encoding='utf-8',newline='\n')
 p=d/'joint266_tb.sv';s=p.read_text(encoding='utf-8')
 s=once(s,'repeat(4)@(negedge clk);reset=0;', '''repeat(4)@(negedge clk);reset=0;
  repeat(20)@(negedge host_clk);wr261(24'h006006,8'ha5);
  wait(!dut.flow.invalidate_banks);''')
 p.write_text(s,encoding='utf-8',newline='\n')
 for name in ['nes_joint269.py','probe_nes_refill269.py']:
  f=Path(__file__).with_name(name);(d/name).write_bytes(f.read_bytes());pins[name]=sha(f)
 return src,pins


def prepare(*args,**kwargs):
 src,pins=old.prepare(*args,**kwargs);return patch(args[0],src,pins)


def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'refill269-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
