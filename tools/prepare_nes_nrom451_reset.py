# SPDX-License-Identifier: MIT
"""Prepare isolated sink admission reset candidate from a specified board."""
import argparse,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();shutil.copytree(a.board,a.out,ignore=shutil.ignore_patterns('db','incremental_db','output_files','simulation'))
f=a.out/'nes_sink_bridge165.sv';s=f.read_text();old='always @(posedge clk or posedge raw_cancel)begin\n  if(raw_cancel)begin idle_ss<=0;idle_write<=0;host_ready<=0;end';new='always @(posedge clk or posedge reset)begin\n  if(reset)begin idle_ss<=0;idle_write<=0;host_ready<=0;end';assert s.count(old)==1;f.write_text(s.replace(old,new))
names=['nes_domain_reset124.sv','nes_sink_bridge165.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','sink-program.hex'];sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();(a.out/'preparation.json').write_text(json.dumps({'sources':{n:sha(a.out/n) for n in names},'scope':'candidate host admission local reset; not yet production or FIT/STA signoff'},indent=2)+'\n')
