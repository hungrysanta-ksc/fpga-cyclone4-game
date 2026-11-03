# SPDX-License-Identifier: MIT
"""572 START plus diagnostic CDC and one host-local reset owner."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_start572 import prepare as start572

def prepare(base,out):
    start572(base,out,'loader')
    p=out/'nes_screen_status151.sv';s=p.read_text()
    s=once(s,'sck_sync,mosi_sync,active_sync;','sck_sync,mosi_sync,active_sync,drive_sync;')
    s=once(s,'wr_sync<=3;rd_sync<=3;active_sync<=0;','wr_sync<=3;rd_sync<=3;active_sync<=0;drive_sync<=0;')
    s=once(s,'active_sync<={active_sync[0],active};','active_sync<={active_sync[0],active};drive_sync<={drive_sync[0],bus_drive};')
    s=once(s,'error_code,bus_drive,active_sync[1]','error_code,drive_sync[1],active_sync[1]')
    p.write_text(s,newline='\n')
    p=out/'nes_sink_bridge165.sv';s=p.read_text()
    s=once(s,'input wire clk,raw_reset,active,stop,','input wire clk,raw_reset,active,stop,\n output wire session_release_reset,')
    s=once(s,'(* altera_attribute=', 'assign session_release_reset=reset;\n (* altera_attribute=')
    s=once(s,'always @(posedge clk or posedge raw_cancel)begin\n  if(raw_cancel)begin idle_ss<=0;idle_write<=0;host_ready<=0;end',
           'always @(posedge clk or posedge reset)begin\n  if(reset)begin idle_ss<=0;idle_write<=0;host_ready<=0;end')
    p.write_text(s,newline='\n')
    p=out/'fxpak_nes_screen137_top.sv';s=p.read_text()
    s=once(s,'always @(posedge host_clk or posedge core_reset)\n  if(core_reset)sink_rom_fault<=0;',
           'wire host_cancel_reset;\n always @(posedge host_clk or posedge host_cancel_reset)\n  if(host_cancel_reset)sink_rom_fault<=0;')
    s=once(s,'nes_sink_bridge165 sink(.clk(host_clk),','nes_sink_bridge165 sink(.session_release_reset(host_cancel_reset),.clk(host_clk),')
    p.write_text(s,newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
