# SPDX-License-Identifier: MIT
"""Generate isolated SPI START and memory admission changes on the fitted 571 A sources."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_bus571 import prepare as aperture571


def prepare(base, out, mode):
    aperture571(base, out)
    if mode in ('loader', 'joint', 'revocable'):
        path = out / 'nes_rom_spi.sv'
        source = once(path.read_text(), ' always @(posedge mem_clk or posedge reset)begin\n  if(reset)begin\n   approved_pulse', ''' // approved START and a pending STOP/CHECK_BEGIN are mutually exclusive.
 // Use the queued response itself at START retirement; keep every live veto.
 wire start_ok = !fault && ss_sync[1] && !check_fault && !(check_enable && boot_fault) &&
                 (!response_queued471 || (check_enable && check_busy && response_low471 && response_high471));
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   approved_pulse''')
        source = once(source, '{check_request,stop,start,load_end,load_valid,load_begin}<=retire_low & retire_high & {6{retire_base_ok}};',
                      '''{check_request,stop}<=retire_low[5:4] & retire_high[5:4] & {2{retire_base_ok}};
   start<=approved_pulse[3] && start_ok;
   {load_end,load_valid,load_begin}<=retire_low[2:0] & retire_high[2:0] & {3{retire_base_ok}};''')
        path.write_text(source, newline='\n')
    if mode == 'revocable':
        path = out / 'nes_diag_clock_guard127.sv'
        source = once(path.read_text(), 'else if(ref_age==63)ref_fault<=1;',
                      'else if(ref_age==63)begin ref_fault<=1;ref_qualified<=0;end')
        source = once(source, 'else if(mem_age==671)mem_fault<=1;',
                      'else if(mem_age==671)begin mem_fault<=1;mem_qualified<=0;end')
        source = once(source, 'always @(posedge mem_clk or posedge guard_mem_reset)\n  if(guard_mem_reset)ref_ok_mem<=0;else ref_ok_mem<={ref_ok_mem[0],ref_qualified};',
                      """// A lost reference grant trips this chain even if mem_clk has stopped.
 always @(posedge mem_clk or negedge ref_qualified)
  if(!ref_qualified)ref_ok_mem<=0;else ref_ok_mem<={ref_ok_mem[0],1'b1};""")
        source = once(source, 'assign allow_memory=!reset&&ref_ok_mem[1]&&mem_qualified&&!fault;',
                      'assign allow_memory=ref_ok_mem[1]&&mem_qualified;')
        path.write_text(source, newline='\n')
        path = out / 'nes_live_joint.sv'
        source = once(path.read_text(), '.kill(guard_reset||guard_fault)', '.kill(guard_reset||!guard_allow)')
        path.write_text(source, newline='\n')
    if mode in ('memory', 'joint'):
        path = out / 'nes_diag_clock_guard127.sv'
        source = once(path.read_text(), 'assign allow_memory=!reset&&ref_ok_mem[1]&&mem_qualified&&!fault;',
                      'assign allow_memory=!reset&&ref_ok_mem[1]&&mem_qualified;')
        path.write_text(source, newline='\n')
        path = out / 'nes_live_joint.sv'
        source = once(path.read_text(), ' nes_clock_release563 memory_release(.clk(mem_clk),.kill(guard_reset||guard_fault),',
                      ''' // The heartbeat fault is sticky until guard_reset. Inhibit external admission
 // immediately. Only a common reset can rearm the internal startup timer.
 wire startup_reset;
 assign release_memory=startup_reset || guard_reset || guard_fault;
 nes_clock_release563 memory_release(.clk(mem_clk),.kill(guard_reset),''')
        source = once(source, '.qualified(guard_allow),.reset_out(release_memory));',
                      '.qualified(guard_allow),.reset_out(startup_reset));')
        source = once(source, 'startup(.clk(mem_clk),.reset(release_memory)', 'startup(.clk(mem_clk),.reset(startup_reset)')
        path.write_text(source, newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['loader', 'memory', 'joint', 'revocable'], required=True)
    args = parser.parse_args()
    prepare(args.base, args.out, args.mode)
