# SPDX-License-Identifier: MIT
"""C0 raw eligibility capture, C1 causes, C2 decode, C3 accept, C4 counter."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import sha
from nes_loadcount167 import transform as loader

def transform(s):
 a=s.index(' wire [4:0] body_causes;');b=s.index(' // Preserve the prior error precedence:',a)
 s=s[:a]+''' // C0 samples external eligibility separately from command aggregation.
 // These are the original C0 values, never a prior-cycle prediction.
 reg sampled;
 reg [4:0] raw_causes;
 reg [3:0] raw_select;
 reg raw_loaded,raw_run,raw_ready,raw_load_ready;
 wire [4:0] static_causes;
 assign static_causes[0]=command<8'h60 || command>8'h6a;
 assign static_causes[1]=(offset_zero_command && offset!=0) ||
  (offset_length_command && offset!={5'd0,loaded_bytes});
 assign static_causes[2]=((cmd60 || cmd61 || cmd62 || cmd63) && check_enable) ||
  (cmd66 && (check_enable || offset!=0)) ||
  (cmd67 && (!check_enable || check_busy || check_done || !offset_matches_next || !next_below_length));
 assign static_causes[3]=1'b0;
 assign static_causes[4]=(cmd63 && !verified) ||
  (cmd68 && (!check_enable || check_busy || !check_done || !offset_matches_next || arg!=checked_data)) ||
  (cmd69 && (!check_enable || check_busy || check_done || !next_matches_length || offset!={5'd0,loaded_bytes}));
 wire [4:0] sampled_causes={
  raw_causes[4] || (raw_select[3] && (!raw_loaded || raw_run)),
  raw_select[0] && !raw_load_ready,
  raw_causes[2] || (raw_select[1] && (!raw_loaded || raw_run)) || (raw_select[2] && !raw_ready),
  raw_causes[1:0]};
'''+s[b:]
 replacements=[
 ('captured<=0;decoded_error<=0;',"sampled<=0;raw_causes<=0;raw_select<=0;raw_loaded<=0;raw_run<=0;raw_ready<=0;raw_load_ready<=0;captured<=0;decoded_error<=0;"),
 ('pending<=captured;captured<=0;', 'pending<=captured;captured<=sampled;sampled<=0;\n   if(sampled)pending_causes<=sampled_causes;'),
 ('(captured || pending || counter_commit_pending) && !ss_sync[1]', '(sampled || captured || pending || counter_commit_pending) && !ss_sync[1]'),
 ('!fault && !captured && !pending && !counter_commit_pending)begin', '!fault && !sampled && !captured && !pending && !counter_commit_pending)begin'),
 ('captured<=1;pending_command<=command[3:0];pending_arg<=arg;', 'sampled<=1;pending_command<=command[3:0];pending_arg<=arg;'),
 ('pending_causes<=body_causes;', 'raw_causes<=static_causes;raw_select<={cmd63,cmd67,cmd66,cmd61};\n     raw_loaded<=loaded;raw_run<=run_enable;raw_ready<=check_ready;raw_load_ready<=load_ready;')]
 for a,b in replacements:assert s.count(a)==1,a;s=s.replace(a,b)
 s=s.replace('//167 ID74 wire-compatible at >=2us SS-high: C0 capture/C1 decode/C2 accept.\n// CHECK counter alone commits on C3; this is NOT same-edge equivalence.', '//167 ID74 >=2us SS-high: C0 raw/C1 causes/C2 decode/C3 accept/C4 counter.\n// Adds one cycle to command acceptance; NOT same-edge equivalence.')
 s=s.replace('// Adds one mem_clk after capture. New frames during either queued stage fail closed.', '// All queued stages reject SS overlap; hard faults stay live on every edge.')
 s=s.replace('C2 is the command acceptance boundary. C3 records', 'C3 is the command acceptance boundary. C4 records')
 s=s.replace('Only this counter moves one edge.', 'Counter commit remains one edge after acceptance.')
 s=s.replace('// C1 validates and decodes the command. C2 applies ONLY live fault/SS', '// C2 validates and decodes the command. C3 applies ONLY live fault/SS')
 s=s.replace('// gating to the pulse registers. No error delay and no extra clock stage.', '// gating to the pulse registers. Hard faults are not delayed.')
 return s

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 m=json.loads((baseline/'preparation.json').read_bytes())
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 for n,fn in [('nes_rom_spi.sv',transform),('nes_rom_loader.sv',loader)]:
  p=out/n;old=p.read_text();new=fn(old);p.write_text(new,encoding='utf8',newline='\n')
  (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],changed=['nes_rom_spi.sv','nes_rom_loader.sv'],
  public_sources={'tools/nes_rawstage167.py':sha(Path(__file__)),'tools/nes_loadcount167.py':sha(Path(__file__).with_name('nes_loadcount167.py'))},
  extra_command_cycles=1,counter_after_accept_cycles=1,min_ss_high_ns=2000,spi_identity=116)
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
