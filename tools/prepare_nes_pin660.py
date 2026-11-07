"""Keep CDC request and reply tags in NES order; interleave on the registered pin address only."""
import argparse
from pathlib import Path
from prepare_nes_word660 import board
from nes_raw506 import once


def build(base,out):
    board(base,out,shared=True,one_word=True)
    boot=(base/"nes_rom_boot.sv").read_text()
    boot=once(once(boot,"(input wire clk,mem_clk","(output wire [15:0] bg_word,input wire clk,mem_clk"),".rom_data(rom_data),",".rom_data(rom_data),.bg_word(bg_word),")
    (out/"nes_rom_boot.sv").write_text(boot,newline="\n")
    path=out/"nes_rom_physical.sv";s=path.read_text()
    s=once(s,"output reg [21:0] psram_address","output wire [21:0] psram_address")
    s=once(s," reg chip,lane;",""" reg chip,lane;reg [21:0] logical_pins;
 wire is_chr=logical_pins[19:15]==5'h10;
 wire pin_lane=is_chr?logical_pins[1]:lane;
 wire pin_chip=is_chr?lane:chip;
 assign psram_address={logical_pins[21:2],is_chr?{logical_pins[0],chip}:logical_pins[1:0]};""")
    # layout is applied AFTER address_hold, so the source-side delayed byte
    # selection must use logical bit 3 for CHR, logical bit 0 for PRG.
    s=once(s,"assign rom_data=address_hold[0]?","wire response_lane=address_hold[21:17]==5'h10 ? address_hold[3]:address_hold[0];\n assign rom_data=response_lane?")
    s=once(s,"assign check_data=lane?","assign check_data=pin_lane?")
    s=once(s,"check_response_address={psram_address","check_response_address={logical_pins")
    s=s.replace("psram_address<=","logical_pins<=").replace("chip_active<=chip?","chip_active<=pin_chip?")
    path.write_text(s,newline="\n")
    bind_address(out)
    resolve_reset_pins(out)
    # Same bound for all 16 bits of the unified word as the original low byte.
    p=out/"board.sdc";s=p.read_text().replace("set_max_delay 23.808 -from $src660","set_max_delay 11.904 -from $src660");p.write_text(s,newline="\n")


def bind_address(out):
    # The BASE drives this CHECK output directly from registers. Its logical
    # value is identical here, but the registers now precede the pin mux.
    p=out/"cdc181.sdc";s=p.read_text()
    anchor=' if {[get_collection_size $r]!=1}'
    resolve=r""" if {[get_collection_size $r]==0 && [regexp {^(.*nes_rom_physical:reader)\|check_response_address\[(\d+)\]$} $name -> path bit]} {
  if {$bit==0} {set name "${path}|lane"} elseif {$bit==1} {set name "${path}|chip"} else {
   set name [format {%s|logical_pins[%d]} $path [expr {$bit-2}]]
  }
  set r [get_registers -nowarn $name]
  if {[get_collection_size $r]==0 && [info exists aliases659($name)]} {
   set name $aliases659($name)
   set r [get_registers $name]
  }
 }
"""
    p.write_text(once(s,anchor,resolve+anchor),newline="\n")


def resolve_reset_pins(out):
    p=out/"cdc576.sdc";s=p.read_text()
    p.write_text(once(s," set pinname [regsub"," set regname [get_node_info -name [cdc181_exact $regname]]\n set pinname [regsub"),newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();build(a.base,a.out)
