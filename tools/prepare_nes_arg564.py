# SPDX-License-Identifier: MIT
"""Predecode the SPI loader argument enable on the preceding bit."""
import argparse
from pathlib import Path
from prepare_nes_guard563 import prepare as guard563
from nes_raw506 import once


def prepare(base,out):
    guard563(base,out)
    p=out/'nes_rom_spi.sv'
    s=once(p.read_text(),' reg [3:0] byte_count;', ''' reg [3:0] byte_count;
 // The seventh sampled bit prepares the write enable for the eighth.
 reg arg_write;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)arg_write<=0;
  else if(ss_sync[1])arg_write<=0;
  else if(sck_sync[1] && !sck_previous)arg_write<=bit_count==6 && byte_count==4;
 end''')
    s=once(s,'     case(byte_count)','     if(arg_write)arg<=incoming;\n     case(byte_count)')
    p.write_text(once(s,'4:arg<=incoming;5:arg_not<=incoming;', '5:arg_not<=incoming;'),newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('base','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
