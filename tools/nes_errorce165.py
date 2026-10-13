# SPDX-License-Identifier: MIT
"""Separate error-event enable from command-priority code without new latency."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 assert s.count('error_code<=code;')==1 and s.count('error_code<=0;')==2
 s=s.replace('error_code<=code;','').replace('error_code<=0;','')
 marker=' // State has a single owner.'
 assert s.count(marker)==1
 logic=''' // State qualifies the update; the accepted command selects the code.
 // This is the original priority on the same edge, including STOP+VALID.
 wire error_begin=accepted_load_begin && (state==RECEIVE || state==RUN || timed_phase);
 wire error_start=accepted_start && (state==IDLE || state==RECEIVE || state==RUN || timed_phase);
 wire error_end=accepted_load_end && (state==IDLE || state==READY || state==RUN || timed_phase || (state==RECEIVE && !count_complete));
 wire error_valid=accepted_load_valid && (state==IDLE || state==READY || state==RUN || (state==RECEIVE && count_complete));
 wire error_stop=stop && (state==WRITE || state==HOLD);
 wire error_event=command_conflict || error_stop || (!stop && (error_begin || error_start || error_end || error_valid));
 always @(posedge mem_clk or posedge reset)begin
  if(reset)error_code<=0;
  else if(active_reset)error_code<=0;
  else if(!fault && error_event)
   error_code<=command_conflict?4'd5:stop?4'd6:accepted_load_begin?4'd1:accepted_start?4'd3:accepted_load_end?4'd2:4'd4;
 end

'''
 return s.replace(marker,logic+marker)

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_loader.sv').read_text();new=transform(old)
 (out/'nes_rom_loader.sv').write_text(new)
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_loader.sv'],public_sources={'tools/nes_errorce165.py':sha(Path(__file__))})
 assert [n for n,h in r['sources'].items() if h!=m['sources'][n]]==r['changed']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
