"""Exercise the fitted ROM inputs and board-top boot bus at four host-clock phases."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

from package_nes_trial704 import read, sha

ROOT=Path(__file__).resolve().parents[1]


def check(temp,out,bin_dir,variant):
    out.mkdir(parents=True)
    def run(exe,args,log):
        with (out/log).open('wb') as f:
            subprocess.run([bin_dir/(exe+'.exe'),*args],cwd=out,stdout=f,
                           stderr=subprocess.STDOUT,check=True,timeout=1200)
    board=temp/'nes-trial816-board890'
    prior=temp/'nes-trial816-board872'
    report=read(ROOT/'analysis/trial890-package.json')['board']
    assert report['changed_board_inputs']==['sink-program.hex']
    project=(board/'board.qsf').read_text()
    files=re.findall(r'^set_global_assignment -name (VHDL|VERILOG|SYSTEMVERILOG)_FILE (\S+)',project,re.M)
    assert files and sha(board/'board.qsf')==sha(prior/'board.qsf')
    for kind,name in files:
        assert sha(board/name)==sha(prior/name)
        dest=out/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(board/name,dest)
    for p in board.rglob('*'):
        if p.suffix in ('.vh','.svh','.mif') and p.is_file() and not {'db','incremental_db'}.intersection(p.relative_to(board).parts):
            dest=out/p.relative_to(board)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,dest)
    run('vmap',['-c'],'vmap.log')
    run('vlib',['work'],'vlib.log')
    for i,(kind,name) in enumerate(files):
        if kind=='VHDL':
            run('vcom',['-2008',name],f'vcom-{i}.log')
    run('vlog',['-sv','-mfcu',*[n for k,n in files if k!='VHDL'],
                ROOT/'tools/nes_boot891_tb.sv'],'vlog.log')
    results={}
    for n,source in [(872,prior),(890,board),(891,temp/f'nes-trial816-board{variant}')]:
        if n==891:
            name='nes_screen_status151.sv'
            shutil.copyfile(source/name,out/name)
            defines=['+define+WITNESS891']
            if variant in ('891D','891E'):
                defines.append('+define+COMPACT891')
            run('vlog',['-sv',*defines,name,ROOT/'tools/nes_boot891_tb.sv'],'vlog-witness.log')
        image=source/'sink-program.hex'
        actual=bytes.fromhex(image.read_text())
        fitted_source=board if n==891 else source
        fitted,=(fitted_source/'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
        pairs=sorted((int(a),int(b,2)) for a,b in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',fitted.read_text(),re.M))
        assert [i for i,_ in pairs]==list(range(5120)) and bytes(v for _,v in pairs)==actual
        shutil.copyfile(image,out/'sink-program.hex')
        log=f'simulation-{n}.log'
        run('vsim',['-c','-L','altera_mf_ver','-L','cycloneive_ver',
                    'work.nes_boot891_tb','-do','onerror {quit -code 1};run -all;quit -f'],log)
        text=(out/log).read_text(errors='replace')
        assert 'PASS BOOT891' in text,log
        rows=[dict(x.split('=') for x in line.split()) for line in re.findall(r'^# BOOT891 (.+)$',text,re.M)]
        assert len(rows)==28
        results[str(n)]=dict(program_sha256=sha(image),cases=rows)
    assert results['872']['cases']==results['890']['cases']
    for old,new in zip(results['890']['cases'],results['891']['cases'],strict=True):
        assert old.keys()==new.keys() and all(old[k]==new[k] for k in old if k!='order')
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--bin',type=Path,default=Path('C:/altera_standard/25.1std/questa_fse/win64'))
    p.add_argument('--variant',choices=['891','891B','891C','891D','891E'],default='891')
    a=p.parse_args()
    result=check(a.temp,a.out,a.bin,a.variant)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
