# SPDX-License-Identifier: MIT
"""Hold the CHECK request tag separately from the next-address counter."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
    needle=' reg check_busy,check_done,verified;'
    assert s.count(needle)==1
    s=s.replace(needle,needle+'''
 // Captured only when a validated READ retires. While check_busy, the
 // counter cannot advance: ACK needs !busy; STOP/reset/fault clear busy.
 // Compare the live response against this immutable request tag, keeping
 // the response-edge error check outside the next-counter feedback cone.
 reg [18:0] check_request_tag;''')
    assert s.count('check_response_address!=check_next')==2
    s=s.replace('check_response_address!=check_next','check_response_address!=check_request_tag')
    needle=' // Dynamic faults/response ownership still win on the retirement edge.'
    assert s.count(needle)==1
    return s.replace(needle,''' // Capturing even a rejected READ is harmless: it cannot leave busy set.
 // Keep live-response error decoding out of the tag's own capture enable.
 always @(posedge mem_clk or posedge reset)
  if(reset)check_request_tag<=0;
  else if(pending && pending_command==4'h7)check_request_tag<=check_next;
'''+needle)

def prepare(baseline,out):
    assert not out.exists() and str(out).isascii()
    v=json.loads((ROOT/'analysis/predecode165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==v['raw_result_sha256']['map03']
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    p=out/'nes_rom_spi.sv';old=p.read_text();new=transform(old);p.write_text(new,encoding='utf8')
    (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
    result=dict(baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=['nes_rom_spi.sv'],public_sources={'tools/nes_tag165.py':sha(Path(__file__))})
    assert [n for n,h in result['sources'].items() if h!=result['baseline'][n]]==['nes_rom_spi.sv']
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
