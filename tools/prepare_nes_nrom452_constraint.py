# SPDX-License-Identifier: MIT
"""Apply the existing 5.3 ns loader budget to its actual one-hot phase registers."""
import argparse,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();shutil.copytree(a.board,a.out,ignore=shutil.ignore_patterns('db','incremental_db','output_files','simulation'))
f=a.out/'board.sdc';s=f.read_text();old='*|loader|state*';new='*|loader|phase*';assert s.count(old)==1;f.write_text(s.replace(old,new))

q=(a.out/'board.qsf').read_text();names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP|MIF)_FILE (\S+)',q);missing=[n for n in names if not (a.out/n.strip('\"')).exists()];assert not missing,missing
