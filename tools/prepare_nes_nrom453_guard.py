# SPDX-License-Identifier: MIT
"""Prepare isolated candidate: local asynchronous-assert memory release owns readiness."""
import argparse,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();assert not a.out.exists();shutil.copytree(a.board,a.out,ignore=shutil.ignore_patterns('db','incremental_db','output_files','simulation'))
f=a.out/'nes_live_joint.sv';s=f.read_text();old='assign external_memory_ready=guard_allow && !release_memory && startup_ready;';new='assign external_memory_ready=!release_memory && startup_ready;';assert s.count(old)==1;f.write_text(s.replace(old,new))

q=(a.out/'board.qsf').read_text();names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP|MIF)_FILE (\S+)',q);missing=[n for n in names if not (a.out/n.strip('\"')).exists()];assert not missing,missing
