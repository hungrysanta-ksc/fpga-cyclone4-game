# SPDX-License-Identifier: MIT
"""Separate loader state retirement from fault/error/data side effects."""
from pathlib import Path
import argparse,json,re,shutil,difflib
from nes_game147 import ROOT,sha

STATE=''' // State has a single owner. Error-code priority remains in the original block.
 // WRITE/HOLD never shorten a pulse: a new bad command holds this edge;
 // the already-latched fault drains the phase from the following edge.
 always @(posedge mem_clk or posedge reset)begin
  if(reset)state<=IDLE;
  else if(active_reset)state<=IDLE;
  else case(state)
   WRITE,HOLD:begin
    if(fault || (!stop && (commands_blocked || !(load_begin || load_end || start))))
     if(remaining==1)state<=(state==WRITE)?HOLD:RELEASE;
   end
   SETUP,RELEASE:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_begin || accepted_start || accepted_load_end)state<=FAILED;
    else if(remaining==1)state<=(state==SETUP)?WRITE:RECEIVE;
   end
   IDLE,READY:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_begin)state<=RECEIVE;
    else if(accepted_start)state<=(state==READY)?RUN:FAILED;
    else if(accepted_load_end || accepted_load_valid)state<=FAILED;
   end
   RECEIVE:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_begin || accepted_start)state<=FAILED;
    else if(accepted_load_end)state<=count_complete?READY:FAILED;
    else if(accepted_load_valid)state<=count_complete?FAILED:SETUP;
   end
   RUN:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=READY;
    else if(accepted_load_begin || accepted_start || accepted_load_end || accepted_load_valid)state<=FAILED;
   end
   default:if(fault || command_conflict)state<=FAILED;
  endcase
 end
'''

def transform(s):
 start=s.index(' task automatic fail(');end=s.index('\n wire count_stop=',start)
 original=s[start:end]
 # Preserve the timer process and all data/fault/error-code assignments exactly.
 changed=re.sub(r'state<=[^;]+;',';',original)
 changed=changed.replace('if(state!=WRITE && state!=HOLD);','')
 a=changed.index(' task automatic advance_phase;');b=changed.index(' end endtask',a)+len(' end endtask')
 changed=changed[:a]+' task automatic advance_phase;begin end endtask'+changed[b:]
 assert 'state<=' not in changed and original.count('state<=')==17
 return s[:start]+changed+'\n'+STATE+s[end:]

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 pub=json.loads((ROOT/'analysis/release165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==pub['raw_result_sha256']['map01']
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_loader.sv').read_text();new=transform(old)
 (out/'nes_rom_loader.sv').write_text(new)
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),
  changed=['nes_rom_loader.sv'],public_sources={'tools/nes_state165.py':sha(Path(__file__))})
 assert [n for n,h in result['sources'].items() if h!=m['sources'][n]]==result['changed']
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
