# SPDX-License-Identifier: MIT
"""Factor sticky-fault guard at the existing loader RUN destination."""
import argparse,re,shutil
from pathlib import Path
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def transform(s):
 s=once(s,''' wire ir_bad=fault || accepted_load_end ||
  (!commands_blocked && ((load_begin && (start || stop || load_valid)) || (start && (stop || load_valid))));''',''' wire ir_command_bad=accepted_load_end ||
  (!commands_blocked && ((load_begin && (start || stop || load_valid)) || (start && (stop || load_valid))));
 wire ir_bad=fault || ir_command_bad;''')
 s=once(s,''' wire to_run=(phase[READY] && !ir_bad && !stop && !accepted_load_begin && accepted_start) ||
  (phase[RUN] && !run_bad && !stop && !accepted_load_valid);''',''' wire to_run=!fault && ((phase[READY] && !ir_command_bad && !stop && !accepted_load_begin && accepted_start) ||
  (phase[RUN] && !accepted_load_begin && !accepted_start && !accepted_load_end && !stop && !accepted_load_valid));''')
 return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();assert not a.out.exists();shutil.copytree(a.board,a.out,ignore=shutil.ignore_patterns('db','incremental_db','output_files','simulation','work'));f=a.out/'nes_rom_loader.sv';f.write_text(transform(f.read_text()));q=(a.out/'board.qsf').read_text();names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP|MIF)_FILE (\S+)',q);missing=[n for n in names if not (a.out/n.strip('"')).exists()];assert not missing,missing
