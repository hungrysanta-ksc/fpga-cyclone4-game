"""Compare final ARM plans on the town hardware-core replay and field PPU fetch replay."""
import argparse
import json
import re
import hashlib
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from check_ff3_battle1047 import captured, replay, runtime_modes
from replay_nes_mask820 import simulate

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent/'probes/nes-ff3-1048'

def field_rtl(raw,board,out,kind,first=224,last=227):
    subprocess.run([sys.executable,ROOT/'tools/prepare_nes_geometry230.py','--capture',raw,'--prior',raw,
        '--out',out,'--first',str(first),'--last',str(last),'--chr-ram-type',str(kind)],check=True)
    writes={f:mask for f,_,mask,_ in (map(int,row.split()) for row in (raw/'walk.tsv').read_text().splitlines()[1:])}
    fragment=(ROOT/'tests/nes-functional/ff3_checkpoint_tb.sv').read_text()
    fragment=fragment[fragment.index('    $display("GEOMETRY'):fragment.index('   end\n  end',fragment.index('    $display("GEOMETRY'))]
    fragment=fragment.replace('proof_frame','f').replace('collector.','frame.')
    def adapt(s):
        s=s.replace('nes_native_frame201 frame(.*);',"nes_native_frame201 #(.TILE_QUERY(0)) frame(.snapshot_conflict(1'b0),.query_index({1'b0,query_index}),.*);")
        s=s.replace('.start_permitted(1\'b1)',".clean_pages(clean_pages),.chr_unchanged(&clean_pages),.start_permitted(1'b1)")
        mask=' : '.join(f"f=={f} ? 8'h{(255^writes[f]):02x}" for f in range(first+1,last+1))+" : 8'h00"
        s=s.replace('reg enable=0;',f'wire [7:0] clean_pages;\n reg enable=0;')
        s=s.replace('string name;', f'string name;\n assign clean_pages={mask};')
        return s.replace('done=0;records=0;', '$display("CLEAN_PAGES %0d %02h",f,clean_pages);\n'+fragment+'\n   done=0;records=0;')
    with tempfile.TemporaryDirectory(prefix='ff3-field-rtl-') as tmp:
        scratch=Path(tmp)
        shutil.copytree(board,scratch/'core')
        for ext in ('hex','palette'):
            for p in out.glob(f'frame*.{ext}'):shutil.copyfile(p,scratch/p.name)
        try:
            simulate(scratch/'core',scratch,[(first,last)],adapt=adapt)
        finally:
            for p in scratch.glob('*.log'):shutil.copyfile(p,out/p.name)

def compare(log,out):
    lines=log.read_text(errors='replace')
    masks={int(f):int(v,16) for f,v in re.findall(r'CLEAN_PAGES (\d+) ([0-9A-Fa-f]{2})',lines)}
    captures=list(captured(log))
    assert len(captures)>=3
    clean={f:v==255 for f,v in masks.items()}
    old=ROOT.parent/'probes/nes-ff3-1047/link/src'
    new=WORK/'link-final/src'
    runtime_modes(new,page_history=True)
    result={}
    for label,src,candidate in [('1047',old,False),('1048',new,True)]:
        rows=replay(src,captures,clean,candidate,1,pages=masks,profile=True)
        result[label]=rows
    assert all(x['image']==y['image'] for x,y in zip(*result.values(),strict=True))
    binaries={k:hashlib.sha256((src/'obj-nes-100/firmware.stm').read_bytes()).hexdigest()
              for k,src in [('1047',old),('1048',new)]}
    out.write_text(json.dumps(dict(binaries=binaries,frames=result),indent=2)+'\n')
    for k,rows in result.items():
        print(k,len(rows),{v:sum(r[v] for r in rows) for v in ['tile_bytes','descriptor_bytes','planner_instructions']})

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['field','compare'])
    ap.add_argument('source',type=Path)
    ap.add_argument('out',type=Path)
    ap.add_argument('--chr-ram-type',type=int)
    a=ap.parse_args()
    if a.action=='field':field_rtl(a.source.resolve(),WORK/'board-io',a.out.resolve(),a.chr_ram_type)
    else:compare(a.source,a.out)
