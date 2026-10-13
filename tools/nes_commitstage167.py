# SPDX-License-Identifier: MIT
"""C2 accepts a checked action; C3 commits only its counter effect."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 old=' always @(posedge mem_clk or posedge reset)\n  if(reset)check_next<=0;\n  else if(counter_retire_ok)begin\n   if(pending_counter_clear)check_next<=0;\n   else if(pending_counter_inc)begin'
 assert s.count(old)==1
 new=''' // C2 is the command acceptance boundary. C3 records the accepted
 // counter effect. Later faults do not undo an already accepted command;
 // asynchronous reset cancels the record. Only this counter moves one edge.
 // Legal SPI observes it after >=2us SS-high, far after both edges settle.
 reg commit_clear,commit_inc;
 wire counter_commit_pending=commit_clear || commit_inc;
 always @(posedge mem_clk or posedge reset)
  if(reset)begin commit_clear<=0;commit_inc<=0;end
  else begin
   commit_clear<=counter_retire_ok && pending_counter_clear;
   commit_inc<=counter_retire_ok && pending_counter_inc;
  end
 always @(posedge mem_clk or posedge reset)
  if(reset)check_next<=0;
  else begin
   if(commit_clear)check_next<=0;
   else if(commit_inc)begin'''
 s=s.replace(old,new)
 s=s.replace('(captured || pending) && !ss_sync[1]','(captured || pending || counter_commit_pending) && !ss_sync[1]')
 s=s.replace('!fault && !captured && !pending)begin','!fault && !captured && !pending && !counter_commit_pending)begin')
 s=s.replace('//165 experimental ID74: SS capture, decode, retirement on three distinct edges.','//167 ID74 wire-compatible at >=2us SS-high: C0 capture/C1 decode/C2 accept.\n// CHECK counter alone commits on C3; this is NOT same-edge equivalence.')
 return s

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 n='nes_rom_spi.sv';old=(out/n).read_text();new=transform(old);(out/n).write_text(new,encoding='utf8',newline='\n')
 (out/'commit.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],changed=[n],baseline_preparation_sha256=sha(baseline/'preparation.json'),public_sources={'tools/nes_commitstage167.py':sha(Path(__file__))},counter_extra_mem_cycles=1,same_edge_equivalence=False,spi_identity=0x74,min_ss_high_ns=2000)
 assert [n for n,h in r['sources'].items() if h!=m['sources'][n]]==r['changed']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
