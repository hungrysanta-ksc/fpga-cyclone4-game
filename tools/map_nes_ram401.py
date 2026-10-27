# SPDX-License-Identifier: MIT
"""Lite RAM-shape check only: independent previous-row and rank read/write ports.
Not an implemented capture pipeline, control replacement or whole-board MAP.
"""
import argparse,json,subprocess
from pathlib import Path
from nes_delta231 import sha

SOURCE='''// SPDX-License-Identifier: MIT
module ram401(input wire clk,prev_we,rank_we,input wire[5:0]prev_waddr,prev_raddr,
input wire[2:0]rank_waddr,rank_raddr,input wire[14:0]prev_data,
input wire[61:0]rank_data,output reg[14:0]prev_q,output reg[61:0]rank_q);
(* ramstyle="M9K, no_rw_check" *)reg[14:0]previous[0:32];
(* ramstyle="M9K, no_rw_check" *)reg[61:0]rank[0:7];
always @(posedge clk)begin
 if(prev_we)previous[prev_waddr]<=prev_data;
 prev_q<=previous[prev_raddr];
 if(rank_we)rank[rank_waddr]<=rank_data;
 rank_q<=rank[rank_raddr];
end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 (d/'ram401.sv').write_text(SOURCE,newline='\n')
 (d/'shape.qpf').write_text('PROJECT_REVISION = "shape"\n')
 (d/'shape.qsf').write_text('set_global_assignment -name FAMILY "Cyclone IV E"\nset_global_assignment -name DEVICE EP4CE15F17C8\nset_global_assignment -name TOP_LEVEL_ENTITY ram401\nset_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files\nset_global_assignment -name SYSTEMVERILOG_FILE ram401.sv\nset_global_assignment -name NUM_PARALLEL_PROCESSORS 2\n')
 with(d/'map.log').open('wb')as log:r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','shape'],cwd=d,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=240)
 assert r.returncode==0
 rpt=(d/'output_files/shape.map.rpt').read_text();assert 'Analysis & Synthesis was successful'in rpt
 result=dict(passed=True,scope=__doc__,whole_MAP=False,pipeline_function_verified=False,source=sha(d/'ram401.sv'),report=sha(d/'output_files/shape.map.rpt'))
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
