"""The source cache holds the accepted miss key through the physical reply and STOP drain."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_short660 import build as short_board


def build(base,out):
    short_board(base,out)
    p=out/"nes_native_arbiter165.sv";s=p.read_text()
    s=once(s,"module nes_native_arbiter165(","module nes_native_arbiter165 #(parameter SOURCE_HOLDS_KEY=0)(")
    s=once(s," wire grant=",""" wire [21:0] expected_address=SOURCE_HOLDS_KEY?fill_address:held_address;
 wire [15:0] expected_generation=SOURCE_HOLDS_KEY?fill_generation:held_generation;
 wire grant=""").replace("assign fill_response_generation=held_generation;","assign fill_response_generation=expected_generation;").replace("mem_response_address!=held_address","mem_response_address!=expected_address")
    p.write_text(s,newline="\n")
    p=out/"nes_source_tile192.sv";s=p.read_text()
    p.write_text(once(s," nes_native_arbiter165 arbiter("," nes_native_arbiter165 #(.SOURCE_HOLDS_KEY(USE_CACHE)) arbiter("),newline="\n")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();build(a.base,a.out)
