# SPDX-License-Identifier: MIT
"""Guard-local asynchronous assertion and clock-domain release candidate."""
import argparse,re,shutil
from pathlib import Path
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def transform(s):
 s=once(s,' reg mem_heartbeat=0;reg [4:0] fast_divider=0;', ''' wire guard_ref_reset,guard_mem_reset;
 nes_domain_reset124 ref_release(.clk(ref_clk),.raw_reset(reset),.reset(guard_ref_reset));
 nes_domain_reset124 mem_release(.clk(mem_clk),.raw_reset(reset),.reset(guard_mem_reset));
 reg mem_heartbeat=0;reg [4:0] fast_divider=0;''')
 assert s.count('posedge mem_clk or posedge reset')==3 and s.count('posedge ref_clk or posedge reset')==3
 s=s.replace('posedge mem_clk or posedge reset','posedge mem_clk or posedge guard_mem_reset').replace('posedge ref_clk or posedge reset','posedge ref_clk or posedge guard_ref_reset')
 # Each original reset condition must be replaced in its own always block only.
 s=once(s,'if(reset)begin mem_heartbeat<=0;','if(guard_mem_reset)begin mem_heartbeat<=0;')
 s=once(s,'if(reset)ref_divider<=0;','if(guard_ref_reset)ref_divider<=0;')
 s=once(s,'if(reset)mem_sync<=0;','if(guard_ref_reset)mem_sync<=0;')
 s=once(s,'if(reset)ref_sync<=0;','if(guard_mem_reset)ref_sync<=0;')
 s=once(s,'if(reset)begin\n   mem_seen<=0;', 'if(guard_ref_reset)begin\n   mem_seen<=0;')
 s=once(s,'if(reset)begin\n   ref_seen<=0;', 'if(guard_mem_reset)begin\n   ref_seen<=0;')
 return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();assert not a.out.exists();shutil.copytree(a.board,a.out,ignore=shutil.ignore_patterns('db','incremental_db','output_files','simulation','work'));f=a.out/'nes_diag_clock_guard127.sv';f.write_text(transform(f.read_text()));q=(a.out/'board.qsf').read_text();names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP|MIF)_FILE (\S+)',q);missing=[n for n in names if not (a.out/n.strip('"')).exists()];assert not missing,missing
