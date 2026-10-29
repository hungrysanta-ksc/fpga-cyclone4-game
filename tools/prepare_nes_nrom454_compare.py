# SPDX-License-Identifier: MIT
"""Split C0 offset/length comparisons while preserving same-edge sampled causes."""
import argparse,re,shutil
from pathlib import Path
def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def transform(s):
 s=once(s,' reg [3:0] raw_select;',' reg [3:0] raw_select;\n reg raw_len_command,raw_end_command,raw_len_lo_diff,raw_len_hi_diff;')
 s=once(s," (offset_length_command && offset!={5'd0,loaded_bytes});",' 1\'b0;')
 s=once(s,"!next_matches_length || offset!={5'd0,loaded_bytes}));","!next_matches_length));")
 s=once(s,'  raw_causes[4] || (raw_select[3] && (!raw_loaded || raw_run)),','  raw_causes[4] || (raw_end_command && (raw_len_lo_diff || raw_len_hi_diff)) || (raw_select[3] && (!raw_loaded || raw_run)),')
 s=once(s,'  raw_causes[1:0]};','  raw_causes[1] || (raw_len_command && (raw_len_lo_diff || raw_len_hi_diff)),raw_causes[0]};')
 s=once(s,'sampled<=0;raw_causes<=0;raw_select<=0;captured<=0;', 'sampled<=0;raw_causes<=0;raw_select<=0;raw_len_command<=0;raw_end_command<=0;raw_len_lo_diff<=0;raw_len_hi_diff<=0;captured<=0;')
 s=once(s,'     raw_causes<=static_causes;raw_select<={cmd63,cmd67,cmd66,cmd61};', '''     raw_causes<=static_causes;raw_select<={cmd63,cmd67,cmd66,cmd61};
     raw_len_command<=offset_length_command;raw_end_command<=cmd69;
     raw_len_lo_diff<=offset[11:0]!=loaded_bytes[11:0];
     raw_len_hi_diff<=offset[23:12]!={5'd0,loaded_bytes[18:12]};''')
 return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();assert not a.out.exists();shutil.copytree(a.board,a.out,ignore=shutil.ignore_patterns('db','incremental_db','output_files','simulation','work'));f=a.out/'nes_rom_spi.sv';f.write_text(transform(f.read_text()));q=(a.out/'board.qsf').read_text();names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP|MIF)_FILE (\S+)',q);missing=[n for n in names if not (a.out/n.strip('"')).exists()];assert not missing,missing
