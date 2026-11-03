# SPDX-License-Identifier: MIT
"""Measure transfer cancellation and the unchanged first real capture boundary."""
import argparse,json,re,subprocess
from pathlib import Path
from nes_raw506 import once,sha


def main():
    p=argparse.ArgumentParser()
    for n in ('base','board','bin','out'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();d=a.out;d.mkdir(parents=True,exist_ok=False)
    tests=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    (d/'reference.sv').write_text(once((a.base/'nes_source_epoch207.sv').read_text(),'module nes_source_epoch207(','module epoch572('))
    s=(tests/'epoch573_tb.sv').read_text()
    s=once(s,'if(reference!=={source_ready,source_is_rom,source_writing,live_epoch})',
           'if(reference[34:32]!=={source_ready,source_is_rom,source_writing} || (source_ready && reference[31:0]!==live_epoch))')
    s=once(s,'  @(posedge source_ready);ready_at=tick;',
           '  if(!epoch.complete)$fatal(1,"transfer missed core release");\n  @(posedge source_ready);ready_at=tick;')
    s=once(s,' integer tick=0,checks=0;bit armed=0;',
           ' integer tick=0,checks=0;bit armed=0;\n'+(tests/'serial574_tile.svh').read_text())
    s=once(s,'tick-start_at);\n endtask','tick-start_at);\n  first_tile574(pass,start_at);\n endtask')
    (d/'capture.sv').write_text(s)
    reference=once(s,'module epoch573_tb;','module capture574_reference;')
    reference=once(reference,'nes_source_epoch207 epoch(.*);','epoch572 epoch(.*);')
    reference=once(reference,'if(!epoch.complete)$fatal(1,"transfer missed core release");','')
    (d/'reference-capture.sv').write_text(reference)
    def run(tool,args,name,marker=None):
        log=d/(name+'.log')
        with log.open('wb') as f:
            subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=180,check=True)
        s=log.read_text(errors='replace')
        if marker and (marker not in s or '** Fatal:' in s):raise AssertionError((name,s[-900:]))
        return s
    run('vlib',['work'],'lib')
    log=run('vlog',['-sv','-y',a.board,'+libext+.sv',d/'reference.sv',d/'capture.sv',d/'reference-capture.sv',tests/'serial574_tb.sv'],'compile')
    phases=[]
    for phase in (0,1):
        flags=['+SHIFT'] if phase else []
        s=run('vsim',['-c','serial574_tb',*flags,'-do','run -all; quit -f'],'transfer'+str(phase),'PASS574 transfer=226')
        run('vsim',['-c','serial574_tb',*flags,'+SKEW','-do','run -all; quit -f'],'skew'+str(phase),'PASS574 transfer=226')
        s=run('vsim',['-c','epoch573_tb',*flags,'-do','run -all; quit -f'],'capture'+str(phase),'PASS573 comparisons=')
        rows=re.findall(r'FIRST573 (\d+) (\w+) (\d+) (\d+) (\d+) (\d+)',s)
        assert len(rows)==3
        tiles=re.findall(r'TILE574 (\d+) first_request=(\d+) cache_epoch=(\w+)',s)
        assert len(tiles)==3
        ref=run('vsim',['-c','capture574_reference',*flags,'-do','run -all; quit -f'],'reference'+str(phase),'PASS573 comparisons=')
        assert re.findall(r'TILE574 (\d+) first_request=(\d+) cache_epoch=(\w+)',ref)==tiles
        assert re.findall(r'FIRST573 (\d+) (\w+) (\d+) (\d+) (\d+) (\d+)',ref)==rows
        phases.append(rows)
    modules={f.name:sha(f) for f in a.board.glob('nes_*.sv') if re.search(r'Compiling module '+f.stem+r'\b',log)}
    # Prove the late-data stimulus can detect insufficient request settling.
    mutant=(a.board/'nes_source_epoch207.sv').read_text().replace('request_nes[2]','request_nes[1]')
    (d/'negative.sv').write_text(mutant)
    run('vlog',['-sv',d/'negative.sv'],'negative-compile')
    negative=run('vsim',['-c','serial574_tb','+SKEW','-do','run -all; quit -f'],'negative')
    assert 'mixed identity' in negative and 'PASS574' not in negative,negative[-900:]
    (d/'result.json').write_text(json.dumps(dict(phases=phases,modules=modules,reference=sha(a.base/'nes_source_epoch207.sv'),transfer_cases=226,skew_negative='mixed identity'),indent=2)+'\n')


if __name__=='__main__':main()
