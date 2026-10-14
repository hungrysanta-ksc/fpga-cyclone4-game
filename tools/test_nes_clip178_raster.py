# SPDX-License-Identifier: MIT
"""Only the changed raster admission boundary; no replay or physical timing claim."""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess
from nes_game147 import ROOT, sha
from nes_clip178 import raster

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    assert not a.out.exists();a.out.mkdir()
    name='nes_native_raster_frame165.sv'
    pins=json.loads((ROOT/'analysis/boundary177-verification.json').read_bytes())['verification']['sources']
    assert sha(a.baseline/name)==pins[name]
    (a.out/name).write_text(raster((a.baseline/name).read_text()),encoding='utf8',newline='\n')
    tb='tests/nes-functional/native_clip178_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
    def call(exe,args,label):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:]
        return s
    call('vlib',['work'],'vlib');call('vlog',['-sv',name,Path(tb).name],'vlog')
    s=call('vsim',['-c','work.native_clip178_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'raster')
    m=re.search(r'PASS CLIP178 frames=(\d+) checks=(\d+)',s);assert m
    r=dict(passed=True,frames=int(m[1]),checks=int(m[2]),baseline_sha256=pins[name],candidate_sha256=sha(a.out/name),
           public_sources={n:sha(ROOT/n) for n in [tb,'tools/nes_clip178.py','tools/test_nes_clip178_raster.py']},
           scope='256 uniform masks, inter-row/midline changes, invalid-to-valid recovery and fault retirement. Synthetic rows; not whole-game/shared-memory/export/SNES timing.')
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(m[0])

if __name__=='__main__':main()
