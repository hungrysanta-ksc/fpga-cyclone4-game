# SPDX-License-Identifier: MIT
"""State-lookahead command legality; no accepted-command latency change.

Unlike compare165's combinational state/error flattening, four registered
legality bits track the next onehot state. Length-dependent RECEIVE tests
remain live. Sticky fault is independent of the detailed error priority mux.
"""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import sha

def transform(s):
 assert s.count('fault<=0;')==2 and s.count('fault<=1;')==1
 s=s.replace('fault<=0;','').replace('fault<=1;','')
 at=s.index(' task automatic fail')
 s=s[:at]+''' // Bits0..3 reject BEGIN/START/END/DATA in state-only cases.
 // Updated from the SAME next-state predicates as phase, not delayed phase.
 (* preserve, dont_merge *) reg [3:0] reject_state;
 wire illegal_begin=load_begin && reject_state[0];
 wire illegal_start=start && reject_state[1];
 wire illegal_end=load_end && (reject_state[2] || (phase[RECEIVE] && !count_complete));
 // Other simultaneous commands are already covered by command_conflict.
 wire illegal_data=load_valid && !stop && (reject_state[3] || (phase[RECEIVE] && count_complete));
 wire local_fault=command_conflict || (stop && (phase[WRITE] || phase[HOLD])) ||
   (!commands_blocked && (illegal_begin || illegal_start || illegal_end || illegal_data));
 always @(posedge mem_clk or posedge reset)
  if(reset)fault<=0;
  else if(active_reset)fault<=0;
  else if(local_fault)fault<=1;
'''+s[at:]
 at=s.index('\n wire count_stop=')
 s=s[:at]+'''
 // State-only legality advances in lockstep even during fault write-drain.
 always @(posedge mem_clk or posedge reset)begin
  if(reset)reject_state<=4'b1110;
  else if(active_reset)reject_state<=4'b1110;
  else begin
   reject_state[0]<=to_receive || to_run || to_setup || to_write || to_hold || to_release;
   reject_state[1]<=to_idle || to_receive || to_run || to_setup || to_write || to_hold || to_release;
   reject_state[2]<=to_idle || to_ready || to_run || to_setup || to_write || to_hold || to_release;
   reject_state[3]<=to_idle || to_ready || to_run;
  end
 end
'''+s[at:]
 return s

def prepare(baseline,out):
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 n='nes_rom_loader.sv';old=(baseline/n).read_text();new=transform(old)
 (out/n).write_text(new,encoding='utf8',newline='\n')
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),newline='\n')
 r=dict(baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=[n],public_sources={'tools/nes_legality174.py':sha(Path(__file__))})
 assert [n for n,h in r['sources'].items() if h!=r['baseline'][n]]==['nes_rom_loader.sv']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
