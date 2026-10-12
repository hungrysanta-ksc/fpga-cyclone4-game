# SPDX-License-Identifier: MIT
"""Reproduce area synthesis and rejected, cycle-preserving OAM experiments.

Default area variant preserves every RTL byte. It is not a fitted design.
"""
from pathlib import Path
import argparse,difflib,json,shutil,re
from nes_game147 import ROOT,sha

def transform(text,variant='row-writer'):
 if variant=='area':return text
 start=text.index('module OAMEval(');end=text.index('endmodule',start)
 old=text[start:end];s=old
 if variant=='row-writer':
  for lane in range(8):
   pattern=rf'always @\(posedge clk\)begin\s+if\(Savestate_OAMWrEn && Savestate_OAMAddr\[2:0\]==3\'d{lane}\).*?\nend'
   matches=list(re.finditer(pattern,s,re.S));assert len(matches)==1
   replacement=f'''wire lane{lane}_normal=oam_copy_write || (oam_cpu_write && oam_read_addr[2:0]==3'd{lane});
wire lane{lane}_save=Savestate_OAMWrEn && Savestate_OAMAddr[2:0]==3'd{lane};
wire [7:0] lane{lane}_data=oam_copy_write ? oam_bank{lane}[oam_row_last] : (is_attr_byte ? (oam_din & 8'hE3) : oam_din);
genvar row{lane};
generate for(row{lane}=0;row{lane}<32;row{lane}=row{lane}+1)begin:write_lane{lane}
 always @(posedge clk)begin
  if(lane{lane}_normal && oam_write_row==row{lane})oam_bank{lane}[row{lane}]<=lane{lane}_data;
  else if(lane{lane}_save && Savestate_OAMAddr[7:3]==row{lane})oam_bank{lane}[row{lane}]<=Savestate_OAMWriteData;
 end
end endgenerate'''
   m=matches[0];s=s[:m.start()]+replacement+s[m.end():]
  return text[:start]+s+text[end:]
 assert variant=='onehot-read'
 a=s.index('function automatic [7:0] oam_read(');b=s.index('endfunction',a)+len('endfunction')
 # Equality terms shared across eight data bits and all constant bank reads.
 funcs=''
 for lane in range(8):
  funcs+=f'''function automatic [7:0] lane{lane}_read(input [4:0] row);
 integer r;begin
 lane{lane}_read=0;
 for(r=0;r<32;r=r+1)lane{lane}_read=lane{lane}_read | (oam_bank{lane}[r] & {{8{{row==r[4:0]}}}});
 end
endfunction
'''
 funcs+='function automatic [7:0] oam_read(input [7:0] address);\n case(address[2:0])\n'
 funcs+=''.join(f" 3'd{i}:oam_read=lane{i}_read(address[7:3]);\n" for i in range(8))
 funcs+=" default:oam_read=8'hxx;\n endcase\nendfunction"
 s=s[:a]+funcs+s[b:]
 for i in range(8):
  target=f'oam_copy_write ? oam_bank{i}[oam_row_last] :'
  assert s.count(target)==1
  s=s.replace(target,f'oam_copy_write ? lane{i}_read(oam_row_last) :')
 return text[:start]+s+text[end:]

def prepare(baseline,out,variant='area'):
 assert not out.exists() and str(out).isascii()
 pub=json.loads((ROOT/'analysis/sink-board165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==pub['raw_result_sha256']['board03']
 meta=json.loads((baseline/'preparation.json').read_bytes())
 out.mkdir(parents=True)
 # Quartus also auto-discovers same-directory modules absent from the QSF.
 archive=json.loads((baseline.parent/'evidence-manifest.json').read_bytes())
 names=sorted(set(meta['sources'])|{p.name for p in baseline.glob('*.sv')}|{'board.qsf','board.qpf','board.sdc','sink-program.hex'})
 for n in names:
  assert sha(baseline/n)==archive[baseline.name+'/'+n],n
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,d)
 p=out/'rtl/ppu.sv';before=p.read_text();after=transform(before,variant)
 if variant!='area':p.write_text(after,encoding='utf8')
 if variant=='area':
  p=out/'board.qsf';p.write_text(p.read_text()+'\nset_global_assignment -name CYCLONEII_OPTIMIZATION_TECHNIQUE AREA\n')
 (out/'oam-select.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='board03/rtl/ppu.sv',tofile='select165/rtl/ppu.sv')),encoding='utf8')
 changed=['board.qsf'] if variant=='area' else ['rtl/ppu.sv']
 result=dict(variant=variant,baseline={n:sha(baseline/n) for n in names},sources={n:sha(out/n) for n in names},public_sources={'tools/nes_oam_select165.py':sha(Path(__file__))},changed=changed)
 assert [n for n in names if result['baseline'][n]!=result['sources'][n]]==changed
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--variant',choices=['row-writer','onehot-read','area'],default='area')
 a=p.parse_args();prepare(a.baseline,a.out,a.variant)
