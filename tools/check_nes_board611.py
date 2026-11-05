"""Exercise the exact board source and capture RAM, without a second license seat."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from check_nes_wire600 import ROOT,pin,read,sha

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    files=['nes_source_tile192.sv','nes_tile205.sv','nes_native_arbiter165.sv','nes_chr_cache611.sv','nes_obj_capture611.sv']
    for n in files:shutil.copy(a.board/n,a.out/n)
    benches=['nes_source_board611_tb','nes_obj_capture611_tb']
    for n in benches:shutil.copy(ROOT/'tools'/(n+'.sv'),a.out)
    pin(a.samples,read(ROOT/'analysis/snoop601-verification.json')['fixture_sha256'])
    shutil.copy(a.samples,a.out/'stim.tsv')
    def exe(tool,args,name):
        with (a.out/(name+'.log')).open('wb') as f:
            subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
    exe('vlib',['work'],'lib');exe('vlog',['-sv',*files,*[n+'.sv' for n in benches]],'compile')
    logs={}
    for n in benches:
        exe('vsim',['-c',n,'-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'],n)
        text=(a.out/(n+'.log')).read_text();assert 'PASS611' in text
        logs[n]=dict(pass_line=next(l for l in text.splitlines() if 'PASS611' in l),sha256=sha(a.out/(n+'.log')))
    (a.out/'result.json').write_text(json.dumps(dict(inputs={n:sha(a.out/n) for n in files},benches={n:sha(a.out/(n+'.sv')) for n in benches},logs=logs),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('board','out','bin','samples'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
