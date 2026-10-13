# SPDX-License-Identifier: MIT
"""Balance the live offset/length comparator without registers or latency."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 assert s.count("offset!={5'd0,loaded_bytes}")==2 and s.count("offset=={5'd0,loaded_bytes}")==1
 marker=' // Framing and lifecycle checks are captured in parallel; effects are delayed.'
 assert s.count(marker)==1
 logic=''' // Eleven first-level LUT-sized equalities, then 4/4/3 reductions.
 // Keep the tree boundaries to avoid a long area-optimized equality cascade.
 // No register: all consumers use the live length on the original edge.
 (* keep = "true" *) wire [10:0] length_pair_equal;
 (* keep = "true" *) wire [2:0] length_group_equal;
'''
 for i in range(9):logic+=f' assign length_pair_equal[{i}]=offset[{2*i+1}:{2*i}]==loaded_bytes[{2*i+1}:{2*i}];\n'
 logic+=''' assign length_pair_equal[9]=offset[19:18]=={1'b0,loaded_bytes[18]};
 assign length_pair_equal[10]=offset[23:20]==4'd0;
 assign length_group_equal[0]=&length_pair_equal[3:0];
 assign length_group_equal[1]=&length_pair_equal[7:4];
 assign length_group_equal[2]=&length_pair_equal[10:8];
 wire live_length_equal=&length_group_equal;
'''
 return s.replace(marker,logic+marker).replace("offset!={5'd0,loaded_bytes}",'!live_length_equal').replace("offset=={5'd0,loaded_bytes}",'live_length_equal')

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 pub=json.loads((ROOT/'analysis/phaseguard165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==pub['raw_result_sha256']['map01']
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_spi.sv').read_text();new=transform(old)
 (out/'nes_rom_spi.sv').write_text(new)
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_spi.sv'],public_sources={'tools/nes_length165.py':sha(Path(__file__))})
 assert [n for n,h in result['sources'].items() if h!=m['sources'][n]]==result['changed']
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
