# SPDX-License-Identifier: MIT
"""Parallel destination equations, retaining all sixteen loader state codes."""
from pathlib import Path
import argparse,json,difflib,shutil
from nes_game147 import ROOT,sha

def transform(s):
 a=s.index(' // State has a single owner.')
 b=s.index('\n wire count_stop=',a)
 new=''' // Each destination is selected independently; encode only after the
 // per-source guards. Preserve numeric codes, including unused-state holds.
 wire from_ir=(state==IDLE || state==READY);
 wire ir_bad=fault || accepted_load_end ||
  (!commands_blocked && ((load_begin && (start || stop || load_valid)) || (start && (stop || load_valid))));
 wire receive_bad=fault || accepted_load_begin || accepted_start ||
  (accepted_load_end && (stop || accepted_load_valid));
 wire timed_bad=fault || accepted_load_begin || accepted_start || accepted_load_end;
 wire run_bad=timed_bad;
 // Fault drains an existing WRITE/HOLD even if STOP is simultaneously set.
 wire drain_step=(fault || (!stop && (commands_blocked || !(load_begin || load_end || start)))) && remaining==1;
 wire to_receive=(from_ir && !ir_bad && !stop && accepted_load_begin) ||
  (state==RECEIVE && !receive_bad && !stop && !accepted_load_end && !accepted_load_valid) ||
  (state==RELEASE && !timed_bad && !stop && remaining==1);
 wire to_write=(state==SETUP && !timed_bad && !stop && remaining==1) ||
  (state==WRITE && !drain_step);
 wire to_hold=(state==WRITE && drain_step) || (state==HOLD && !drain_step);
 wire to_ready=(state==READY && !ir_bad && !stop && !accepted_load_begin && !accepted_start && !accepted_load_valid) ||
  (state==RECEIVE && !receive_bad && !stop && accepted_load_end && count_complete) ||
  (state==RUN && !run_bad && stop);
 wire to_run=(state==READY && !ir_bad && !stop && !accepted_load_begin && accepted_start) ||
  (state==RUN && !run_bad && !stop && !accepted_load_valid);
 wire to_failed=(from_ir && (ir_bad || (!stop && !accepted_load_begin &&
                         ((accepted_start && state==IDLE) || (!accepted_start && accepted_load_valid))))) ||
  (state==RECEIVE && (receive_bad || (!stop && ((accepted_load_end && !count_complete) ||
                         (!accepted_load_end && accepted_load_valid && count_complete))))) ||
  ((state==SETUP || state==RELEASE) && timed_bad) ||
  (state==RUN && (run_bad || (!stop && accepted_load_valid))) ||
  state==FAILED || (state>RELEASE && (fault || command_conflict));
 wire to_setup=(state==RECEIVE && !receive_bad && !stop && !accepted_load_end && accepted_load_valid && !count_complete) ||
  (state==SETUP && !timed_bad && !stop && remaining!=1);
 wire to_release=(state==HOLD && drain_step) ||
  (state==RELEASE && !timed_bad && !stop && remaining!=1);
 wire [3:0] unused_hold=(state>RELEASE && !fault && !command_conflict)?state:4'd0;
 // IDLE is zero. No higher-priority common destination mux is needed.
 wire [3:0] destination=unused_hold |
  ({4{to_receive}} & 4'd1) | ({4{to_write}} & 4'd2) |
  ({4{to_hold}} & 4'd3) | ({4{to_ready}} & 4'd4) |
  ({4{to_run}} & 4'd5) | ({4{to_failed}} & 4'd6) |
  ({4{to_setup}} & 4'd7) | ({4{to_release}} & 4'd8);
 always @(posedge mem_clk or posedge reset)begin
  if(reset)state<=IDLE;
  else if(active_reset)state<=IDLE;
  else state<=destination;
 end
'''
 return s[:a]+new+s[b:]

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_loader.sv').read_text();new=transform(old)
 (out/'nes_rom_loader.sv').write_text(new)
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_loader.sv'],public_sources={'tools/nes_destination165.py':sha(Path(__file__))})
 assert [n for n,h in r['sources'].items() if h!=m['sources'][n]]==r['changed']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
