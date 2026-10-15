# SPDX-License-Identifier: MIT
"""Isolated board181 candidate: six fixed 32:1 palette bit selectors."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
from nes_reject180 import replace

def raster(s):
    s=replace(s,' reg [191:0] held_palette,line_palette;',
        ' reg [191:0] held_palette,line_palette;\n'
        ' // Constant wiring transposes 32 packed colors into six bit lanes.\n'
        ' // A 5-bit color index selects one bit per lane; no variable stride.\n'
        ' wire [5:0] copy_color;\n'
        ' genvar pb,pc;generate for(pb=0;pb<6;pb=pb+1)begin:palette_lane\n'
        '  wire [31:0] bits_by_color;\n'
        '  for(pc=0;pc<32;pc=pc+1)begin:color_bit\n'
        '   assign bits_by_color[pc]=held_palette[6*pc+pb];\n'
        '  end\n'
        '  assign copy_color[pb]=bits_by_color[copy_offset];\n'
        ' end endgenerate')
    return replace(s,'held_palette[copy_offset*6+:6]','copy_color')

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    ref=ROOT/'analysis/board181-verification.json'
    sources=json.loads(ref.read_bytes())['verification']['fits']['map03']['sources']
    a.out.mkdir(parents=True)
    for n,h in sources.items():
        assert sha(a.baseline/n)==h,n
        dst=a.out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,dst)
    f=a.out/'nes_native_raster181.sv';f.write_text(raster(f.read_text()),encoding='utf8',newline='\n')
    result=dict(sources={n:sha(a.out/n) for n in sources},changed=['nes_native_raster181.sv'],
        baseline_analysis_sha256=sha(ref),preparer_sha256=sha(Path(__file__)),hardware=False)
    (a.out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print('Prepared palette selector candidate;',len(sources),'pinned sources')

if __name__=='__main__':main()
