"""Reuse the validated short-form discriminator that already stays live through tile_done."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_emit660 import emit_board


def build(base,out):
    emit_board(base,out)
    def change(name,old,new):
        p=out/name;p.write_text(once(p.read_text(),old,new),newline="\n")
    change("nes_plan_batch206.sv","output wire plan_valid,","output wire plan_short,output wire plan_valid,")
    change("nes_plan_batch206.sv"," assign plan_valid="," assign plan_short=shortform;\n assign plan_valid=")
    change("nes_direct206.sv"," nes_plan_batch206 transport"," wire short_bg660;\n nes_plan_batch206 transport")
    change("nes_direct206.sv",".plan_valid(pv),.plan_ready(tr)",".plan_valid(pv),.plan_short(short_bg660),.plan_ready(tr)")
    change("nes_direct206.sv",".plan_valid(pv&&permit)",".plan_short(short_bg660),.plan_valid(pv&&permit)")
    for name in ("nes_source_tile192.sv","nes_tile205.sv"):
        change(name,"input wire plan_valid,","input wire plan_short,plan_valid,")
    change("nes_source_tile192.sv",".plan_valid(plan_valid&&!fault)",".plan_short(plan_short),.plan_valid(plan_valid&&!fault)")
    change("nes_tile205.sv","wire pair_bg=kind==0 && rows==48'o7766554433221100 && alt_mask==0;",
           "wire pair_bg=kind==0 && EXTERNAL_PLAN!=0 && plan_short;")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();build(a.base,a.out)
