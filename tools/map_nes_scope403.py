# SPDX-License-Identifier: MIT
"""Lite port/width feasibility only; never a whole-board area saving."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(ROOT/'tests/nes-scope403/ram_shape.sv',d/'ram_shape403.sv')
 (d/'shape.qpf').write_text('PROJECT_REVISION = "shape"\n',newline='\n')
 (d/'shape.qsf').write_text('set_global_assignment -name FAMILY "Cyclone IV E"\nset_global_assignment -name DEVICE EP4CE15F17C8\nset_global_assignment -name TOP_LEVEL_ENTITY ram_shape403\nset_global_assignment -name SYSTEMVERILOG_FILE ram_shape403.sv\nset_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files\nset_global_assignment -name NUM_PARALLEL_PROCESSORS 2\n',newline='\n')
 with(d/'map.log').open('wb')as log:r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','shape'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
 report=(d/'output_files/shape.map.rpt').read_text();raw=(d/'map.log').read_text();assert r.returncode==0 and 'Analysis & Synthesis was successful'in report
 assert not re.search(r'RAM logic "[^\n]*(serialized|concurrent|metadata)" is uninferred',raw)
 result=dict(passed=True,whole_MAP=False,pipeline_function_verified=False,scope=__doc__,source=sha(d/'ram_shape403.sv'),report=sha(d/'output_files/shape.map.rpt'),RAM_summary=[x for x in report.splitlines()if re.search(r';\s+(Simple|True) Dual Port\s*;',x)])
 assert len(result['RAM_summary'])==3,result['RAM_summary']
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
