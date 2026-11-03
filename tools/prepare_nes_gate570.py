# SPDX-License-Identifier: MIT
"""Retain the 568 A / 569 datapath and separate remote qualification from plan cancellation."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_plan569 import prepare as plan569


def prepare(base, out, memory_only=False, mask_ingress=False, shared_bulk=False, local_release=False):
    plan569(base, out)
    guard=out/'nes_diag_clock_guard127.sv'
    guard.write_text(once(guard.read_text(),' assign allow_memory=!reset&&ref_qualified&&mem_qualified&&!fault;', ''' // The stable start permission crosses alone. Fault assertion still drives
 // the independent asynchronous kill on memory_release.
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [1:0] ref_ok_mem;
 always @(posedge mem_clk or posedge guard_mem_reset)
  if(guard_mem_reset)ref_ok_mem<=0;else ref_ok_mem<={ref_ok_mem[0],ref_qualified};
 assign allow_memory=!reset&&ref_ok_mem[1]&&mem_qualified&&!fault;'''),newline='\n')
    if memory_only:return
    direct=out/'nes_direct206.sv'
    s=once(direct.read_text(),' always @(posedge nes_clk or posedge nr)', ''' // An asserted NES producer fault closes the host side even when the
 // detecting NES edge is the last edge before a clock stall.
 wire nes_error=lease_fault||tile_fault||core_fault;
 always @(posedge nes_clk or posedge nr)''')
    s=once(s,'if(h_to_n[1]||lease_fault||tile_fault||core_fault)','if(h_to_n[1]||nes_error)')
    s=once(s,'hcancel(.clk(host_clk),.raw_reset(reset||cancel)','hcancel(.clk(host_clk),.raw_reset(reset||cancel||nes_error)')
    s=once(s,"nes_plan_batch206 transport(.host_clk(host_clk),.nes_clk(nes_clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(cancel)",
           "nes_plan_batch206 transport(.host_clk(host_clk),.nes_clk(nes_clk),.reset(reset),.active(1'b1),.stop(hc),.source_fault(1'b0)")
    if mask_ingress or shared_bulk or local_release:
        # A transaction can already own a snapshot and have received its trailer.
        # Its SS rising edge must not increment the accepted count after kill.
        s=once(s,".source_fault(hf),\n  .SPI_SS", ".source_fault(hc),\n  .SPI_SS")
    if shared_bulk or local_release:
        s=once(s,"nes_tile_bulk206 bulk(.nes_clk(nes_clk),.host_clk(host_clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(cancel)",
               "nes_tile_bulk206 bulk(.nes_clk(nes_clk),.host_clk(host_clk),.reset(reset),.active(1'b1),.stop(hc),.source_fault(1'b0)")
    if local_release:
        # hc already asserts asynchronously on common reset; keeping an extra
        # raw-reset input at these children bypasses its synchronized release.
        for instance in ('nes_plan_batch206 transport(.host_clk(host_clk),.nes_clk(nes_clk),',
                         'nes_tile_bulk206 bulk(.nes_clk(nes_clk),.host_clk(host_clk),'):
            suffix=".active(1'b1),.stop(hc),.source_fault(1'b0)"
            s=once(s,instance+'.reset(reset),'+suffix,instance+".reset(1'b0),"+suffix)
    direct.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','out'):p.add_argument('--'+k,type=Path,required=True)
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--memory-only',action='store_true')
    modes.add_argument('--mask-ingress',action='store_true')
    modes.add_argument('--shared-bulk',action='store_true')
    modes.add_argument('--local-release',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.memory_only,a.mask_ingress,a.shared_bulk,a.local_release)
