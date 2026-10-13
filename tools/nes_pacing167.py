# SPDX-License-Identifier: MIT
"""Targeted grant/consumer wait policy; immutable165 sources are transformed."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def fill(s):
 s=s.replace('parameter integer WAIT_CYCLES=1024','parameter integer WAIT_CYCLES=1024,\n parameter COOPERATIVE_WAIT=0')
 s=s.replace('wire time_ok=cycles<MAX_CYCLES && waiting<WAIT_CYCLES;', '''// Waiting for a vblank grant or a consumer is not an accepted-read fault.
 // The total wall-clock budget still bounds BOTH states, including starvation.
 wire short_wait=!(COOPERATIVE_WAIT && (state==REQUEST || state==STREAM));
 wire time_ok=cycles<MAX_CYCLES && (!short_wait || waiting<WAIT_CYCLES);''')
 s=s.replace('else if(waiting>=WAIT_CYCLES)fail(4);','else if(short_wait && waiting>=WAIT_CYCLES)fail(4);')
 # No outstanding short wait survives REQUEST/STREAM; every exit handshake
 # resets it. Wrap in these ignored states is harmless. Avoid a wide reset
 # selector on every waiting-counter bit; retain the original increment CE.
 s=s.replace('reg [31:0] waiting;', 'reg [$clog2(WAIT_CYCLES+1)-1:0] waiting;')
 assert 'short_wait' in s and s.count('COOPERATIVE_WAIT')==2
 return s

def exporter(s):
 s=s.replace('input wire fill_busy,fill_done,fill_success,','input wire fill_busy,fill_done,fill_success,input wire [3:0] fill_error,')
 s=s.replace('reg [31:0] cycles;', 'reg [3:0] fill_detail;\n reg [31:0] cycles;')
 s=s.replace("13'd2,60'd0,error", "13'd2,56'd0,fill_detail,error")
 s=s.replace('begin error<=reason;state<=ABORT;release_frame<=1;end','begin error<=reason;fill_detail<=reason==4?fill_error:4\'d0;state<=ABORT;release_frame<=1;end')
 s=s.replace('release_frame<=0;error<=0;end','release_frame<=0;error<=0;fill_detail<=0;end')
 s=s.replace('bytes_count<=0;error<=0;query_kind<=0;', 'bytes_count<=0;error<=0;fill_detail<=0;query_kind<=0;')
 assert s.count('fill_detail<=')==3
 return s

def joint(s):
 a='nes_native_fill165 #(.WAIT_CYCLES(131072),.MAX_CYCLES(2097152))'
 assert s.count(a)==1
 s=s.replace(a,'nes_native_fill165 #(.WAIT_CYCLES(131072),.MAX_CYCLES(16777216),.COOPERATIVE_WAIT(1))')
 a='nes_native_export165 #(.MAX_CYCLES(4194304))';assert s.count(a)==1
 s=s.replace(a,'nes_native_export165 #(.MAX_CYCLES(33554432))')
 a='.fill_success(native_fill_success),';assert s.count(a)==1
 return s.replace(a,a+'.fill_error(native_fill_error),')

def prepare(baseline,out,standard_fit=False,placement_effort=False):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 changes={'nes_native_fill165.sv':fill,'nes_native_export165.sv':exporter,'nes_live_joint.sv':joint}
 for n,fn in changes.items():
  old=(baseline/n).read_text();new=fn(old);(out/n).write_text(new,encoding='utf8',newline='\n')
  (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8',newline='\n')
 if standard_fit:
  q=out/'board.qsf';s=q.read_text();assert 'FITTER_EFFORT' not in s
  s+='\nset_global_assignment -name FITTER_EFFORT STANDARD_FIT\n'
  if placement_effort:s+='set_global_assignment -name PLACEMENT_EFFORT_MULTIPLIER 2.0\n'
  q.write_text(s,encoding='utf8',newline='\n');changes['board.qsf']=None
 result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],changed=list(changes),baseline_result_sha256=sha(baseline/'result.json'),placement_effort=placement_effort,public_sources={'tools/nes_pacing167.py':sha(Path(__file__))})
 assert {n for n,h in result['sources'].items() if h!=m['sources'][n]}==set(changes)
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--standard-fit',action='store_true');p.add_argument('--placement-effort',action='store_true');a=p.parse_args();assert not a.placement_effort or a.standard_fit;prepare(a.baseline,a.out,a.standard_fit,a.placement_effort)
