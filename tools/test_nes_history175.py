# SPDX-License-Identifier: MIT
"""Sparse event history, wrap, STOP/fault retention; no full core simulation."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_lifecycle175 import CHANGED,transform

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    assert not a.out.exists();a.out.mkdir(parents=True)
    m=json.loads((a.candidate/'preparation.json').read_bytes())
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==h and sha(a.baseline/n)==m['baseline'][n],n
        if n in CHANGED:assert (a.candidate/n).read_text()==transform(n,(a.baseline/n).read_text()),n
        else:assert h==m['baseline'][n],n
    tb='tests/nes-functional/native_history175_tb.sv';src='nes_ppu_history157.sv'
    shutil.copy2(ROOT/tb,a.out/Path(tb).name);shutil.copy2(a.candidate/src,a.out/src)
    def run(exe,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
        s=(a.out/(label+'.log')).read_text(errors='replace')
        if negative:assert '** Fatal:' in s and 'page mismatch' in s and 'PASS HISTORY175' not in s,s
        else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s
        return s
    run('vlib',['work'],'vlib')
    run('vlog',['-sv',src,Path(tb).name],'vlog')
    s=run('vsim',['-c','work.native_history175_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'history')
    assert 'PASS HISTORY175' in s
    # Negative mutation writes on every active edge instead of events.
    bad=(a.out/src).read_text().replace(' && (sample_valid175 || freeze)','')
    (a.out/'negative.sv').write_text(bad, newline='\n')
    run('vlog',['-sv','negative.sv',Path(tb).name],'negative-vlog')
    run('vsim',['-c','work.native_history175_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'negative',True)
    r=dict(passed=True,summary=re.search(r'PASS HISTORY175[^\r\n]*',s)[0],negative_detected=True,
           sources=m['sources'],public_sources={n:sha(ROOT/n) for n in [tb,'tools/test_nes_history175.py','tools/nes_lifecycle175.py']},
           logs={p.name:sha(p) for p in a.out.glob('*.log')},scope='Sparse A4 RAM history and exact observational source transform. No physical result or timing approval.')
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(r['summary'])

if __name__=='__main__':main()
