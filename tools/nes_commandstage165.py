# SPDX-License-Identifier: MIT
"""Explicit capture/decode/retire contract; one added mem_clk, experimental ID74."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 def edit(a,b):
  nonlocal s
  assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
 edit('//135: register independent validation causes; encode at unchanged retirement edge.',
      '//165 experimental ID74: SS capture, decode, retirement on three distinct edges.')
 edit('// CHECK/read/ack/finish retains protocol0x59. New frames during retirement fail closed.',
      '// Adds one mem_clk after capture. New frames during either queued stage fail closed.')
 edit('reg pending;reg [3:0] pending_command,pending_header_error;',
      'reg captured,pending;reg [3:0] decoded_error;\n reg [3:0] pending_command,pending_header_error;')
 edit('pending_counter_clear<=0;pending_counter_inc<=0;pending<=0;',
      'captured<=0;decoded_error<=0;pending_counter_clear<=0;pending_counter_inc<=0;pending<=0;')
 edit('   pending<=0;\n   if(!fault)begin', '''   // Each stage is a pulse. A transient hard fault latches fault and therefore
   // cancels the command even if it has disappeared by the retirement edge.
   pending<=captured;captured<=0;
   if(captured)begin
    decoded_error<=pending_header_error!=0?pending_header_error:pending_body_error;
    pending_counter_clear<=pending_header_error==0 && pending_causes==0 &&
      (pending_command==0 || pending_command==4 || pending_command==6);
    pending_counter_inc<=pending_header_error==0 && pending_causes==0 && pending_command==8;
   end
   if(!fault)begin''')
 edit('else if(pending && !ss_sync[1])fail(1);','else if((captured || pending) && !ss_sync[1])fail(1);')
 edit('if(pending_header_error!=0)fail(pending_header_error);\n      else if(pending_body_error!=0)fail(pending_body_error);',
      'if(decoded_error!=0)fail(decoded_error);')
 edit('if(!ss_previous && ours && !fault && !pending)begin\n     pending<=1;',
      'if(!ss_previous && ours && !fault && !captured && !pending)begin\n     captured<=1;')
 a=s.index('     pending_counter_clear<=counter_header_ok &&');b=s.index('\n    end',a)
 s=s[:a]+s[b:]
 assert s.count("8'h6b,flags")==2;s=s.replace("8'h6b,flags","8'h74,flags")
 return s

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 v=json.loads((ROOT/'analysis/phaseguard165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==v['raw_result_sha256']['map01']
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_spi.sv').read_text();new=transform(old)
 (out/'nes_rom_spi.sv').write_text(new)
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_spi.sv'],public_sources={'tools/nes_commandstage165.py':sha(Path(__file__))},added_mem_cycles=1,experimental_spi_identity=0x74,installable=False)
 assert [n for n,h in r['sources'].items() if h!=m['sources'][n]]==r['changed']
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
