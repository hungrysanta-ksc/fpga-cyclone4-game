# SPDX-License-Identifier: MIT
"""Synchronize positive clock qualification; keep asynchronous sticky-fault shutdown."""
import argparse
from pathlib import Path
from prepare_nes_owner562 import prepare as owner562
from nes_raw506 import once


def prepare(base,out):
    owner562(base,out)
    p=out/'nes_live_joint.sv'
    p.write_text(once(p.read_text(),
        ' nes_domain_reset124 memory_release(.clk(mem_clk),.raw_reset(guard_reset||!guard_allow),.reset(release_memory));',
        ''' // Both heartbeat counters qualify once per reset. Cross their rising
 // permission on memory edges; a sticky fault must still cut a stopped clock.
 nes_clock_release563 memory_release(.clk(mem_clk),.kill(guard_reset||guard_fault),
  .qualified(guard_allow),.reset_out(release_memory));'''),newline='\n')
    p=out/'nes_diag_clock_guard127.sv'
    p.write_text(p.read_text()+'''
module nes_clock_release563(input wire clk,kill,qualified,output wire reset_out);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [1:0] release_pipe;
 always @(posedge clk or posedge kill)
   if(kill)release_pipe<=0;
   else release_pipe<={release_pipe[0],qualified};
 assign reset_out=!release_pipe[1];
endmodule
''',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('base','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
